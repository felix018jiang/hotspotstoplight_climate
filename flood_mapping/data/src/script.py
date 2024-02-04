import os
import json
import time
import ee
import geemap
from geemap import geojson_to_ee
from datetime import datetime
from data_utils.make_training_data import make_training_data
from data_utils.export_and_monitor import export_and_monitor
from google.cloud import storage

### setup------------------------------------------------------------

# initialize
cloud_project = 'hotspotstoplight'
ee.Initialize(project = cloud_project)

# load aoi
file_path = os.path.join(os.path.dirname(__file__), '../../data/inputs/san_jose_aoi/resourceshedbb_CostaRica_SanJose.geojson')
absolute_path = os.path.abspath(file_path)

with open(absolute_path) as f:
    json_data = json.load(f)

aoi = geojson_to_ee(json_data) # need as a feature collection, not bounding box
bbox = aoi.geometry().bounds()

# Load list of dates with tuples, converting strings to datetime.date objects
flood_dates = [
    (datetime.strptime('2023-10-05', '%Y-%m-%d').date(), datetime.strptime('2023-10-05', '%Y-%m-%d').date()),
    (datetime.strptime('2017-10-05', '%Y-%m-%d').date(), datetime.strptime('2017-10-15', '%Y-%m-%d').date()),
    (datetime.strptime('2018-10-07', '%Y-%m-%d').date(), datetime.strptime('2018-10-08', '%Y-%m-%d').date()),
    (datetime.strptime('2016-11-24', '%Y-%m-%d').date(), datetime.strptime('2016-11-26', '%Y-%m-%d').date()),
    (datetime.strptime('2015-10-27', '%Y-%m-%d').date(), datetime.strptime('2015-10-29', '%Y-%m-%d').date()),
    (datetime.strptime('2015-07-06', '%Y-%m-%d').date(), datetime.strptime('2015-07-08', '%Y-%m-%d').date()),
]


### write data to cloud bucket------------------------------------------------------------

# Define your Google Cloud Storage bucket name
bucket = 'hotspotstoplight_floodmapping'  # Replace with your actual bucket name
fileNamePrefix = 'data/inputs/'
scale = 100  # Adjust scale if needed
# Define other parameters as necessary, such as 'region'

print(f"Number of flood events in list: {len(flood_dates)}")

for index, (start_date, end_date) in enumerate(flood_dates):
    
    geotiff = make_training_data(bbox, start_date, end_date)
    geotiff = geotiff.toShort()

    specificFileNamePrefix = f'{fileNamePrefix}input_data_{start_date}'
    export_description = f'input_data_{start_date}'

    # Print the current GeoTIFF being exported
    print(f"Exporting GeoTIFF {index + 1} of {len(flood_dates)}: {export_description}")

    # Adjust the function call as necessary
    export_and_monitor(geotiff, export_description, bucket, specificFileNamePrefix, scale)

# After the loop
print(f"Finished exporting {len(flood_dates)} GeoTIFFs.")

 
### read images from cloud bucket into image collection------------------------------------------------------------
 
def list_gcs_files(bucket_name, prefix):
    """List all files in a GCS bucket folder."""
    storage_client = storage.Client(project=cloud_project)
    blobs = storage_client.list_blobs(bucket_name, prefix=prefix)
    urls = [f"gs://{bucket_name}/{blob.name}" for blob in blobs if blob.name.endswith('.tif')]
    return urls

bucket_name = 'hotspotstoplight_floodmapping'
prefix = 'data/inputs/'
tif_list = list_gcs_files(bucket_name, prefix)
print(tif_list) 
 
print("Reading images from cloud bucket into image collection...") 
 
# Convert each URL to an ee.Image and add to a list.
ee_image_list = [ee.Image.loadGeoTIFF(url) for url in tif_list]

# Convert the list of images into an Earth Engine ImageCollection.
image_collection = ee.ImageCollection.fromImages(ee_image_list)

# Use geemap to print the collection information, for example, size.
info = image_collection.size().getInfo()
print(f'Collection contains {info} images.') 


### use the image collection to train a model------------------------------------------------------------

print("Training model with image collection...")

# Function to perform stratified sampling on each image
def sample_image(image):
    stratified_sample = image.stratifiedSample(
        numPoints=500,  # Adjust the number of points per image as needed
        classBand='flooded_mask',
        region=image.geometry(),
        scale=30,
        seed=0
    ).randomColumn()
    
    # Split into training and testing within each image's sample
    training_sample = stratified_sample.filter(ee.Filter.lt('random', 0.7))
    testing_sample = stratified_sample.filter(ee.Filter.gte('random', 0.7))
    
    return ee.FeatureCollection([training_sample, testing_sample])

# Map the sampling function over the ImageCollection
samples = image_collection.map(sample_image)

# Flatten the results to merge the FeatureCollections from each image
flat_samples = samples.flatten()

# Now, you have a single FeatureCollection with samples from all images
# Next, filter to create the final training and testing datasets
training = flat_samples.filter(ee.Filter.lt('random', 0.7))
testing = flat_samples.filter(ee.Filter.gte('random', 0.7))

# Note: Adjust 'numPoints' in 'sample_image' function based on your desired total sample size

# Set up the Random Forest classifier for flood prediction
inputProperties = image_collection.first().bandNames().remove('flooded_mask')  # Assumes all images have the same band structure

classifier = ee.Classifier.smileRandomForest(10).train(
    features=training,
    classProperty='flooded_mask',
    inputProperties=inputProperties
)

print("Model training completed.")

### evaluate model------------------------------------------------------------


### classify final image------------------------------------------------------------


### write results------------------------------------------------------------