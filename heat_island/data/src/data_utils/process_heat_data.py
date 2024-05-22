import ee
import geemap
from data_utils.monitor_tasks import monitor_tasks
from data_utils.pygeoboundaries import get_adm_ee
from data_utils.export_and_monitor import start_export_task
from data_utils.scaling_factors import apply_scale_factors
from data_utils.cloud_mask import cloud_mask
from data_utils.export_ndvi import export_ndvi_min_max
from data_utils.download_ndvi import download_ndvi_data_for_year
from data_utils.process_annual_data import process_year
from data_utils.process_data_to_classify import process_data_to_classify
from google.cloud import storage
from datetime import datetime
import csv
from io import StringIO
from collections import Counter

import pretty_errors


def process_heat_data(place_name):

    cloud_project = "hotspotstoplight"
    ee.Initialize(project=cloud_project)

    current_year = datetime.now().year

    # Define the range for the previous 5 full calendar years
    years = range(current_year - 6, current_year - 1)

    scale = 90

    snake_case_place_name = place_name.replace(" ", "_").lower()

    aoi = get_adm_ee(territories=place_name, adm="ADM0")
    bbox = aoi.geometry().bounds()

    bucket_name = f"hotspotstoplight_heatmapping"
    directory_name = f"data/{snake_case_place_name}/inputs/"

    storage_client = storage.Client(project=cloud_project)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(directory_name)
    blob.upload_from_string(
        "", content_type="application/x-www-form-urlencoded;charset=UTF-8"
    )

    file_prefix = "ndvi_min_max"

    gcs_bucket = bucket_name

    def process_for_year(year, cloud_project, bucket_name, snake_case_place_name):

        ndvi_min, ndvi_max = download_ndvi_data_for_year(
            year, cloud_project, bucket_name, snake_case_place_name
        )
        image_collection = process_year(year, bbox, ndvi_min, ndvi_max)

        return image_collection

    for year in years:
        export_ndvi_min_max(year, bbox, scale, gcs_bucket, snake_case_place_name)

    image_list = []

    for year in years:
        image = process_for_year(
            year, cloud_project, bucket_name, snake_case_place_name
        )
        image_list.append(image)

    image_collections = ee.ImageCollection.fromImages(image_list)

    def convert_landcover_to_int(image):
        # Convert the 'landcover' band to integer.
        landcover_int = image.select("landcover").toInt()

        # Replace the original 'landcover' band with the converted integer type band.
        # The 'overwrite' parameter ensures the original band is overwritten.
        return image.addBands(landcover_int.rename("landcover"), overwrite=True)

    # Apply the function to each image in the collection.
    image_collections = image_collections.map(convert_landcover_to_int)

    print("Image collections", image_collections.first().getInfo())

    from collections import Counter

    # Sample the land cover values
    sample = (
        image_collections.first()
        .select("landcover")
        .sample(
            region=bbox,
            scale=10,  # Adjust scale as needed to match your image resolution and the granularity you need
            numPixels=10000,  # Number of pixels to sample for estimating class distribution
            seed=0,
            geometries=False,  # Geometry information not required for this step
        )
    )

    # Extract land cover class values from the sample
    sampled_values = sample.aggregate_array("landcover").getInfo()

    # Calculate the histogram (frequency of each class)
    class_histogram = Counter(sampled_values)

    # Total number of samples you aim to distribute across classes
    total_samples = 100000

    # Determine class values (unique land cover classes) and their proportional sample sizes
    class_values = list(class_histogram.keys())
    class_points = [
        int((freq / sum(class_histogram.values())) * total_samples)
        for freq in class_histogram.values()
    ]

    # Define the class names and codes
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

    # Print initial class histogram
    print(
        "Initial Class Histogram:",
        {land_cover_names.get(k, k): v for k, v in class_histogram.items()},
    )

    if not class_histogram:
        print("Error: Failed to generate a class histogram.")
        raise ValueError("Failed to generate a class histogram.")

    # Set the "Built-up", "Grassland", and "Cropland" class sizes equal to 1/2 the total number of pixels
    half_total_samples = total_samples // 2
    if 50 in class_histogram:  # Built-up class code
        class_histogram[50] = half_total_samples
    if 40 in class_histogram:  # Cropland class code
        class_histogram[40] = half_total_samples
    if 30 in class_histogram:  # Grassland class code
        class_histogram[30] = half_total_samples

    # Print updated class histogram
    print(
        "Updated Class Histogram:",
        {land_cover_names.get(k, k): v for k, v in class_histogram.items()},
    )

    # Recalculate class points based on the updated histogram
    class_values = list(class_histogram.keys())
    class_points = [
        int((freq / sum(class_histogram.values())) * total_samples)
        for freq in class_histogram.values()
    ]

    class_band = "landcover"
    n_images = image_collections.size().getInfo()
    samples_per_image = total_samples // n_images

    # Function to apply stratified sampling to an image
    def stratified_sample_per_image(image):
        # Perform stratified sampling
        stratified_sample = image.stratifiedSample(
            numPoints=samples_per_image,
            classBand=class_band,
            region=bbox,
            scale=30,
            seed=0,
            classValues=class_values,
            classPoints=class_points,
            geometries=True,
        )
        # Return the sample
        return stratified_sample

    # Apply the function to each image in the collection
    samples = image_collections.map(stratified_sample_per_image)

    # Flatten the collection of collections into a single FeatureCollection
    stratified_sample = samples.flatten()

    # Split the data into training and testing
    training_sample = stratified_sample.randomColumn()
    training = training_sample.filter(ee.Filter.lt("random", 0.7))
    testing = training_sample.filter(
        ee.Filter.gte("random", 0.7)
    )  # rather than testing on this dataset, we will use the most recent year's data to test

    # Train the Random Forest regression model
    inputProperties = ["longitude", "latitude", "landcover", "elevation"]
    numTrees = 10  # Number of trees in the Random Forest
    regressor = (
        ee.Classifier.smileRandomForest(numTrees)
        .setOutputMode("REGRESSION")
        .train(training, classProperty="median_top5", inputProperties=inputProperties)
    )

    # Sort the filtered collection in descending order by the 'system:time_start' property
    sorted_filtered_collection = image_collections.sort(
        "system:time_start", False
    )  # False for descending order

    # Now, selecting the first image will give you the most recent image in the collection
    recent_image = sorted_filtered_collection.first()

    predicted_image = recent_image.select(inputProperties).classify(regressor)

    # Calculate the squared difference between actual and predicted LST
    squared_difference = (
        recent_image.select("median_top5")
        .subtract(predicted_image)
        .pow(2)
        .rename("difference")
    )

    def export_results_to_cloud_storage(result, result_type, bucket_name, output_path):
        task = ee.batch.Export.table.toCloudStorage(
            collection=ee.FeatureCollection([ee.Feature(None, {"result": result})]),
            description=f"Export {result_type} results",
            bucket=bucket_name,
            fileNamePrefix=output_path,
            fileFormat="CSV",
        )
        task.start()
        print(
            f"Exporting {result_type} results to {output_path} in bucket {bucket_name}."
        )

    # Compute the mean squared error over your area of interest (aoi)
    mean_squared_error = squared_difference.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=bbox,
        scale=scale,  # Adjust scale to match your dataset's resolution
        maxPixels=1e14,
    )

    # Calculate the square root of the mean squared error to get the RMSE
    rmse = mean_squared_error.getInfo()["difference"] ** 0.5

    # Prepare the RMSE result for export
    rmse_result = {"RMSE": rmse}

    # Specify your cloud storage bucket name and output path
    bucket_name = "hotspotstoplight_heatmapping"
    directory_name = f"data/{snake_case_place_name}/outputs/"
    output_path = directory_name + "rmse_results"

    # Export the RMSE result to cloud storage
    export_results_to_cloud_storage(rmse_result, "RMSE", bucket_name, output_path)

    # Process data and classify the image
    image_to_classify = process_data_to_classify(bbox)
    classified_image = image_to_classify.select(inputProperties).classify(regressor)

    # Initialize the storage client
    storage_client = storage.Client(project=cloud_project)
    bucket = storage_client.bucket(bucket_name)

    # Create and upload an empty file to initialize the directory (if needed)
    blob = bucket.blob(directory_name)
    blob.upload_from_string(
        "", content_type="application/x-www-form-urlencoded;charset=UTF-8"
    )

    # Export the predicted image
    # Ensure the filename or path for the predicted image is unique to avoid overwriting
    predicted_image_filename = f"predicted_median_top5_{snake_case_place_name}"  # Example filename, ensure it's unique
    # The function `start_export_task` should handle the export logic, including setting the correct filename/path
    task = start_export_task(
        classified_image,
        f"{place_name} Median temp of top 5 hottest observations",
        bucket_name,
        directory_name + predicted_image_filename,
        scale,
    )
    tasks = [task]
    monitor_tasks(tasks, 600)
