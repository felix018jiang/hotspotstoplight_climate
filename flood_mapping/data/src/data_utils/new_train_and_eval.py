import ee
from google.cloud import storage
import csv
from io import StringIO
import numpy as np
from collections import Counter
import json

from data_utils.monitor_tasks import monitor_tasks

# Initialize the Earth Engine
ee.Initialize()

samples_per_flood_class = 100000


def aggregate_samples(
    image_collection,
    bbox,
    class_values,
    class_points,
    samples_per_image,
    flooded_status,
    landcover_band="landcover",
    flooded_mask_band="flooded_mask",
):
    """Aggregate samples based on flooded status and export as GeoJSON."""

    def process_image(image):
        # Apply stratified sampling based on land cover classes
        condition_mask = image.select(flooded_mask_band).eq(flooded_status)
        masked_image = image.updateMask(condition_mask)
        stratified_samples = masked_image.stratifiedSample(
            numPoints=samples_per_image // len(class_values),
            classBand=landcover_band,
            region=bbox,
            scale=30,
            seed=0,
            geometries=True,
            classValues=class_values,
            classPoints=class_points,
        )
        return stratified_samples

    # Aggregate samples from all images in the collection
    return image_collection.map(process_image).flatten()


def export_samples_to_gcs(samples, bucket_name, filename):
    """Export samples to Google Cloud Storage as GeoJSON."""
    try:
        task = ee.batch.Export.table.toCloudStorage(
            collection=samples,
            description="ExportToGCS",
            bucket=bucket_name,
            fileNamePrefix=filename,
            fileFormat="GeoJSON",
        )
        task.start()
        print(
            f"Export task {task.id} started, exporting samples to gs://{bucket_name}/{filename}"
        )
        return task
    except Exception as e:
        print(f"Failed to create export task: {e}")
        return None


def clean_geometry(geojson):
    """Remove unsupported 'geodesic' property from geometry definitions."""
    for feature in geojson["features"]:
        if "geodesic" in feature["geometry"]:
            del feature["geometry"]["geodesic"]
    return geojson


def read_geojson_from_gcs(bucket_name, filename):
    """Read GeoJSON file from GCS, parse, clean, and convert into ee.FeatureCollection."""

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    geojson_string = blob.download_as_text()

    # print("GeoJSON string downloaded:")
    # print(geojson_string[:500])  # Print first 500 characters to check it's correct

    geojson = json.loads(geojson_string)
    clean_geojson = clean_geometry(geojson)  # Clean the GeoJSON data

    geojson_fc = ee.FeatureCollection(clean_geojson)
    print("FeatureCollection created successfully.")

    return geojson_fc


def calculate_rates(confusion_matrix):
    # Convert to numpy array for easier calculations
    cm = np.array(confusion_matrix)

    TPR = []  # True Positive Rate list
    FPR = []  # False Positive Rate list

    for i in range(len(cm)):
        TP = cm[i, i]
        FN = cm[i, :].sum() - TP
        FP = cm[:, i].sum() - TP
        TN = cm.sum() - (TP + FP + FN + cm[i, i])

        TPR.append(TP / (TP + FN) if TP + FN != 0 else 0)
        FPR.append(FP / (FP + TN) if FP + TN != 0 else 0)

    return TPR, FPR


def export_results_to_cloud_storage(
    accuracyMatrix, description, bucket_name, filePrefix
):
    """Export the error matrix to Google Cloud Storage directly."""
    # Convert the errorMatrix to a feature
    errorMatrixFeature = ee.Feature(None, {"matrix": accuracyMatrix.array()})

    # Create a FeatureCollection
    errorMatrixCollection = ee.FeatureCollection([errorMatrixFeature])

    # Start the export task
    task = ee.batch.Export.table.toCloudStorage(
        collection=errorMatrixCollection,
        description=description,
        bucket=bucket_name,
        fileNamePrefix=f"{filePrefix}",
        fileFormat="CSV",
    )
    task.start()
    print(
        f"Export task {task.id} started, exporting results to gs://{bucket_name}/{filePrefix}/{description}.csv"
    )


def train_and_evaluate_classifier(
    image_collection, bbox, bucket_name, snake_case_place_name
):
    print("Starting training and evaluation process...")
    if not isinstance(image_collection, ee.ImageCollection):
        print("Error: image_collection must be an ee.ImageCollection.")
        return None, None

    n = image_collection.size().getInfo()
    print(f"Number of images in collection: {n}")
    if n == 0:
        print("Error: Image collection is empty.")
        return None, None

    try:
        samples_per_image = int(samples_per_flood_class // n)
        print(f"Samples per flood class per image: {samples_per_image}")
        input_properties = image_collection.first().bandNames().remove("flooded_mask")
        if not input_properties:
            print("Error: No input properties after removing 'flooded_mask'.")
            return None, None

        landcover = ee.Image("ESA/WorldCover/v100/2020").select("Map").clip(bbox)
        sample = landcover.sample(
            region=bbox,
            scale=10,
            numPixels=samples_per_flood_class / 2,
            seed=0,
            geometries=False,
        )
        sampled_values = sample.aggregate_array("Map").getInfo()

        land_cover_names = {
            10: "Tree cover",
            20: "Shrubland",
            30: "Grassland",
            40: "Cropland",
            50: "Built-up",
            60: "Bare / sparse vegetation",
            70: "Snow and ice",
            80: "Permanent water bodies",
            90: "Herbaceous wetland",
            95: "Mangroves",
            100: "Moss and lichen",
        }

        class_histogram = Counter(sampled_values)
        print(
            "Initial Class Histogram:",
            {land_cover_names.get(k, k): v for k, v in class_histogram.items()},
        )
        if not class_histogram:
            print("Error: Failed to generate a class histogram.")
            return None, None

        # Set the "Built-up" class size equal to 1/2 the sum of all other class values
        total_class_values = sum(class_histogram.values()) / 2
        if 50 in class_histogram:  # Built-up class code
            class_histogram[50] = total_class_values
        if 40 in class_histogram:  # crop land class code
            class_histogram[40] = total_class_values
        if 30 in class_histogram:  # grassland class code
            class_histogram[30] = total_class_values

        print(
            "Updated Class Histogram:",
            {land_cover_names.get(k, k): v for k, v in class_histogram.items()},
        )

        class_values = list(class_histogram.keys())
        class_points = [
            int((freq / sum(class_histogram.values())) * samples_per_flood_class)
            for freq in class_histogram.values()
        ]

        flooded_data = aggregate_samples(
            image_collection,
            bbox,
            class_values,
            class_points,
            samples_per_flood_class,
            1,
        )
        unflooded_data = aggregate_samples(
            image_collection,
            bbox,
            class_values,
            class_points,
            samples_per_flood_class,
            0,
        )
        if not flooded_data or not unflooded_data:
            print("Error: Failed to aggregate samples.")
            return None, None

        # Print sample sizes for verification
        print("Flooded sample size:", flooded_data.size().getInfo())
        print("Unflooded sample size:", unflooded_data.size().getInfo())

        # Add a random column to flooded and unflooded data
        flooded_data = flooded_data.randomColumn()
        unflooded_data = unflooded_data.randomColumn()

        # Sampling proportions for training, testing, and validation
        train_split = 0.6
        test_split = 0.2

        # Filter flooded data for training, testing, and validation sets
        flooded_training = flooded_data.filter(ee.Filter.lt("random", train_split))
        flooded_remaining = flooded_data.filter(ee.Filter.gte("random", train_split))

        flooded_testing = flooded_remaining.filter(
            ee.Filter.lt("random", train_split + test_split)
        )
        flooded_validation = flooded_remaining.filter(
            ee.Filter.gte("random", train_split + test_split)
        )

        # Filter unflooded data for training, testing, and validation sets
        unflooded_training = unflooded_data.filter(ee.Filter.lt("random", train_split))
        unflooded_remaining = unflooded_data.filter(
            ee.Filter.gte("random", train_split)
        )

        unflooded_testing = unflooded_remaining.filter(
            ee.Filter.lt("random", train_split + test_split)
        )
        unflooded_validation = unflooded_remaining.filter(
            ee.Filter.gte("random", train_split + test_split)
        )

        # Print sample sizes for verification
        print("Flooded training sample size:", flooded_training.size().getInfo())
        print("Flooded testing sample size:", flooded_testing.size().getInfo())
        print("Flooded validation sample size:", flooded_validation.size().getInfo())

        print("Unflooded training sample size:", unflooded_training.size().getInfo())
        print("Unflooded testing sample size:", unflooded_testing.size().getInfo())
        print(
            "Unflooded validation sample size:", unflooded_validation.size().getInfo()
        )

        # Merge the datasets
        training_samples = flooded_training.merge(unflooded_training)
        testing_samples = flooded_testing.merge(unflooded_testing)
        validation_samples = flooded_validation.merge(unflooded_validation)

        # Print merged dataset sizes for verification
        print("Training sample size:", training_samples.size().getInfo())
        print("Testing sample size:", testing_samples.size().getInfo())
        print("Validation sample size:", validation_samples.size().getInfo())

        if not training_samples or not testing_samples or not validation_samples:
            print("Error: Failed to sample datasets.")
            return None, None, None

        print("Training the classifier...")
        classifier = ee.Classifier.smileRandomForest(10).train(
            features=training_samples,
            classProperty="flooded_mask",
            inputProperties=input_properties,
        )

        print("Evaluating the classifier...")
        test_accuracy = testing_samples.classify(classifier).errorMatrix(
            "flooded_mask", "classification"
        )
        validation_accuracy = validation_samples.classify(classifier).errorMatrix(
            "flooded_mask", "classification"
        )

        print("Exporting results...")
        export_results_to_cloud_storage(
            test_accuracy,
            "Testing",
            bucket_name,
            f"data/{snake_case_place_name}/outputs/testing_results",
        )
        export_results_to_cloud_storage(
            validation_accuracy,
            "Validation",
            bucket_name,
            f"data/{snake_case_place_name}/outputs/validation_results",
        )

        print("Training and evaluation process completed.")
        return input_properties, training_samples
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None, None
