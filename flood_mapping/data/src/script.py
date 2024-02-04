import os
import json
import time
import ee
import geemap
from geemap import geojson_to_ee
from datetime import datetime
from data_utils.write_to_cloud import export_geotiffs_to_bucket
from data_utils.read_from_cloud import read_images_into_collection
from google.cloud import storage

### setup------------------------------------------------------------

cloud_project = 'hotspotstoplight'
ee.Initialize(project = cloud_project)

file_path = os.path.join(os.path.dirname(__file__), '../../data/inputs/san_jose_aoi/resourceshedbb_CostaRica_SanJose.geojson')
absolute_path = os.path.abspath(file_path)

with open(absolute_path) as f:
    json_data = json.load(f)

aoi = geojson_to_ee(json_data)
bbox = aoi.geometry().bounds()

# Define a list of start (left) and end date (right) strings
date_pairs = [
    ('2023-10-05', '2023-10-05'),
    ('2017-10-05', '2017-10-15'),
    ('2018-10-07', '2018-10-08'),
    ('2016-11-24', '2016-11-26'),
    ('2015-10-27', '2015-10-29'),
    ('2015-07-06', '2015-07-08'),
]

flood_dates = [(datetime.strptime(start, '%Y-%m-%d').date(), datetime.strptime(end, '%Y-%m-%d').date()) for start, end in date_pairs]



### create data, write to cloud bucket, read in as image collection------------------------------------------------------------

bucket_name = 'hotspotstoplight_floodmapping'
fileNamePrefix = 'data/inputs/'

export_geotiffs_to_bucket(bucket_name, fileNamePrefix, flood_dates, bbox)

read_images_into_collection(bucket_name, fileNamePrefix)


### use the image collection to train a model------------------------------------------------------------

print("Training model with image collection...")

def sample_image(image):
    stratified_sample = image.stratifiedSample(
        numPoints=500,  # Adjust the number of points per image as needed
        classBand='flooded_mask',
        region=image.geometry(),
        scale=30,
        seed=0
    ).randomColumn()
    
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
# # Classify the image
# classified = image_collection.select(inputProperties).classify(classifier)

# # Assess accuracy
# testAccuracy = testing.classify(classifier).errorMatrix('flooded_mask', 'classification')

# # Calculate accuracy
# accuracy = testAccuracy.accuracy().getInfo()

# # Convert the confusion matrix to an array
# confusionMatrixArray = testAccuracy.array().getInfo()

# # Calculate recall for the positive class (assuming '1' represents the positive class for flooding)
# true_positives = confusionMatrixArray[1][1]  # True positives
# false_negatives = confusionMatrixArray[1][0]  # False negatives
# false_positives = confusionMatrixArray[0][1]  # False positives (non-flooded incorrectly identified as flooded)
# true_negatives = confusionMatrixArray[0][0]  # True negatives (non-flooded correctly identified as non-flooded)
# recall = true_positives / (true_positives + false_negatives)
# false_positive_rate = false_positives / (false_positives + true_negatives)

# print('Confusion Matrix:', confusionMatrixArray)
# print('Accuracy:', accuracy)
# print('Recall:', recall)
# print('False Positive Rate:', false_positive_rate)


### classify final image------------------------------------------------------------
# Set up the Random Forest classifier for flood prediction with probability output
# classifier = ee.Classifier.smileRandomForest(10).setOutputMode('PROBABILITY').train(
#         features=training,
#         classProperty='flooded_mask',
#         inputProperties=inputProperties
#    )

# probabilityImage = image_collection.select(inputProperties).classify(classifier)

### write results------------------------------------------------------------
# geemap.ee_export_image(probabilityImage, filename="costa_rica_flood_probabilities.tif", scale=300, region=aoi)