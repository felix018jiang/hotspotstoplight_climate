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

def process_heat_data(place_name):
    
    cloud_project = 'hotspotstoplight'
    ee.Initialize(project=cloud_project)

    current_year = datetime.now().year

    # Define the range for the previous 5 full calendar years
    years = range(current_year - 6, current_year - 1)

    scale = 90

    snake_case_place_name = place_name.replace(' ', '_').lower()

    aoi = get_adm_ee(territories=place_name, adm='ADM0')
    bbox = aoi.geometry().bounds()
    
    bucket_name = f'hotspotstoplight_heatmapping'
    directory_name = f'data/{snake_case_place_name}/inputs/'

    storage_client = storage.Client(project=cloud_project)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(directory_name)
    blob.upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')

    file_prefix="ndvi_min_max"

    gcs_bucket = bucket_name
    
    
    def process_for_year(year, cloud_project, bucket_name, snake_case_place_name):

        ndvi_min, ndvi_max = download_ndvi_data_for_year(year, cloud_project, bucket_name, snake_case_place_name)
        image_collection = process_year(year, ndvi_min, ndvi_max)

        return image_collection


    for year in years:
        export_ndvi_min_max(year, bbox, scale, gcs_bucket, snake_case_place_name)


    image_list = []

    for year in years:
        image = process_for_year(year, cloud_project, bucket_name, snake_case_place_name)
        image_list.append(image)

    image_collections = ee.ImageCollection.fromImages(image_list)

    # Sample the 'landcover' band of the image within the specified bounding box
    sample = image_collections.first().select('landcover').sample(
    region=bbox,
    scale=10,  # Adjust scale as needed to match your image resolution and the granularity you need
    numPixels=10000,  # Number of pixels to sample for estimating class distribution
    seed=0,
    geometries=False  # Geometry information not required for this step
    )

    # Extract land cover class values from the sample
    # Note: The band name inside aggregate_array should match your band of interest; adjust if necessary
    sampled_values = sample.aggregate_array('landcover').getInfo()

    # Calculate the histogram (frequency of each class)
    class_histogram = Counter(sampled_values)

    print("Class histogram", class_histogram)

    # Total number of samples you aim to distribute across classes
    total_samples = 5000

    # Determine class values (unique land cover classes) and their proportional sample sizes
    class_values = list(class_histogram.keys())
    class_points = [int((freq / sum(class_histogram.values())) * total_samples) for freq in class_histogram.values()]
        
    class_band = 'landcover'

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
            geometries=True
        )
        # Return the sample
        return stratified_sample

    # Apply the function to each image in the collection
    samples = image_collections.map(stratified_sample_per_image)

    # Flatten the collection of collections into a single FeatureCollection
    stratified_sample = samples.flatten()

   # Split the data into training and testing
    training_sample = stratified_sample.randomColumn()
    training = training_sample.filter(ee.Filter.lt('random', 0.7))
    testing = training_sample.filter(ee.Filter.gte('random', 0.7))

    # Train the Random Forest regression model
    inputProperties=['longitude', 'latitude', 'landcover', 'elevation']
    numTrees = 10  # Number of trees in the Random Forest
    regressor = ee.Classifier.smileRandomForest(numTrees).setOutputMode('REGRESSION').train(
        training, 
        classProperty='hot_days', 
        inputProperties=inputProperties
    )

    # Proceed with the classification
    predicted = testing.select(inputProperties).classify(regressor)

    # Calculate the squared difference for the testing data
    squared_difference = testing.select('hot_days').subtract(predicted).pow(2).rename('difference')

    # Reduce the squared differences to get the mean squared difference over your area of interest (aoi)
    mean_squared_error = squared_difference.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=bbox,
        scale=scale,  # Adjust scale to match your dataset's resolution
        maxPixels=1e14
    )

    # Calculate the square root of the mean squared error to get the RMSE
    rmse = mean_squared_error.getInfo()['difference'] ** 0.5

    image_to_classify = process_data_to_classify()
    
    classified_image = image_to_classify.select(inputProperties).classify(regressor)

    bucket_name = f'hotspotstoplight_heatmapping'
    directory_name = f'data/{snake_case_place_name}/outputs/'

    storage_client = storage.Client(project=cloud_project)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(directory_name)
    blob.upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')
    
    # Prepare and upload the CSV containing the RMSE
    csv_file_name = f'rmse_{snake_case_place_name}.csv'  # Ensure this name is unique
    csv_output = StringIO()
    csv_writer = csv.writer(csv_output)
    csv_writer.writerow(['Metric', 'Value'])
    csv_writer.writerow(['RMSE', rmse])
    csv_content = csv_output.getvalue()
    blob = bucket.blob(directory_name + csv_file_name)  # Append the filename to the directory path
    blob.upload_from_string(csv_content, content_type='text/csv')

    # Export the predicted image
    # Ensure the filename or path for the predicted image is unique to avoid overwriting
    predicted_image_filename = f'predicted_hot_days_{snake_case_place_name}.tif'  # Example filename, ensure it's unique
    # The function `start_export_task` should handle the export logic, including setting the correct filename/path
    task = start_export_task(classified_image, f'{place_name} Days over 33 C Prediction', bucket_name, directory_name + predicted_image_filename, scale)
    tasks = [task]
    monitor_tasks(tasks)