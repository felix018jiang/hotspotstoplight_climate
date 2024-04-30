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

samples_per_flood_class = 50000

def aggregate_samples(image_collection, bbox, class_values, class_points, samples_per_image, flooded_status, landcover_band="landcover", flooded_mask_band="flooded_mask"):
    """ Aggregate samples based on flooded status and export as GeoJSON. """
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
            classPoints=class_points
        )
        return stratified_samples

    # Aggregate samples from all images in the collection
    return image_collection.map(process_image).flatten()

def export_samples_to_gcs(samples, bucket_name, filename):
    """ Export samples to Google Cloud Storage as GeoJSON. """
    try:
        task = ee.batch.Export.table.toCloudStorage(
            collection=samples,
            description='ExportToGCS',
            bucket=bucket_name,
            fileNamePrefix=filename,
            fileFormat='GeoJSON'
        )
        task.start()
        print(f"Export task {task.id} started, exporting samples to gs://{bucket_name}/{filename}")
        return task
    except Exception as e:
        print(f"Failed to create export task: {e}")
        return None


def clean_geometry(geojson):
    """Remove unsupported 'geodesic' property from geometry definitions."""
    for feature in geojson['features']:
        if 'geodesic' in feature['geometry']:
            del feature['geometry']['geodesic']
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

def export_results_to_cloud_storage(accuracyMatrix, description, bucket_name, filePrefix):
    """ Export the error matrix to Google Cloud Storage directly. """
    # Convert the errorMatrix to a feature
    errorMatrixFeature = ee.Feature(None, {'matrix': accuracyMatrix.array()})
    
    # Create a FeatureCollection
    errorMatrixCollection = ee.FeatureCollection([errorMatrixFeature])
    
    # Start the export task
    task = ee.batch.Export.table.toCloudStorage(
        collection=errorMatrixCollection,
        description=description,
        bucket=bucket_name,
        fileNamePrefix=f"{filePrefix}",
        fileFormat='CSV'
    )
    task.start()
    print(f"Export task {task.id} started, exporting results to gs://{bucket_name}/{filePrefix}/{description}.csv")

def train_and_evaluate_classifier(image_collection, bbox, bucket_name, snake_case_place_name):
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
        sample = landcover.sample(region=bbox, scale=10, numPixels=25000, seed=0, geometries=False)
        sampled_values = sample.aggregate_array("Map").getInfo()

        class_histogram = Counter(sampled_values)
        print(class_histogram)
        if not class_histogram:
            print("Error: Failed to generate a class histogram.")
            return None, None

        class_values = list(class_histogram.keys())
        class_points = [int((freq / sum(class_histogram.values())) * samples_per_image) for freq in class_histogram.values()]

        flooded_data = aggregate_samples(image_collection, bbox, class_values, class_points, samples_per_flood_class, 1)
        unflooded_data = aggregate_samples(image_collection, bbox, class_values, class_points, samples_per_flood_class, 0)
        if not flooded_data or not unflooded_data:
            print("Error: Failed to aggregate samples.")
            return None, None

        print("Merging datasets...")
        all_samples = flooded_data.merge(unflooded_data)
        if not all_samples:
            print("Error: Failed to merge datasets.")
            return None, None
        all_samples = all_samples.randomColumn()

        print("Preparing datasets...")
        training_samples = all_samples.filter(ee.Filter.lt("random", 0.6))
        testing_samples = all_samples.filter(ee.Filter.gte("random", 0.6).And(ee.Filter.lt("random", 0.8)))
        validation_samples = all_samples.filter(ee.Filter.gte("random", 0.8))

        print("Training the classifier...")
        classifier = ee.Classifier.smileRandomForest(10).train(features=training_samples, classProperty="flooded_mask", inputProperties=input_properties)
        
        print("Evaluating the classifier...")
        test_accuracy = testing_samples.classify(classifier).errorMatrix("flooded_mask", "classification")
        validation_accuracy = validation_samples.classify(classifier).errorMatrix("flooded_mask", "classification")

        print("Size of testing samples:", testing_samples.size().getInfo())
        print("Size of validation samples:", validation_samples.size().getInfo())

        print("Exporting results...")
        export_results_to_cloud_storage(test_accuracy, "Testing", bucket_name, f"data/{snake_case_place_name}/outputs/testing_results")
        export_results_to_cloud_storage(validation_accuracy, "Validation", bucket_name, f"data/{snake_case_place_name}/outputs/validation_results")

        print("Training and evaluation process completed.")
        return input_properties, all_samples
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None, None




