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
    # ('2016-11-24', '2016-11-26'), EEException: Image.gt: If one image has no bands, the other must also have no bands. Got 0 and 1.
    # ('2015-10-27', '2015-10-29'), ""
    # ('2015-07-06', '2015-07-08'), ""
]

flood_dates = [(datetime.strptime(start, '%Y-%m-%d').date(), datetime.strptime(end, '%Y-%m-%d').date()) for start, end in date_pairs]



### create data, write to cloud bucket, read in as image collection------------------------------------------------------------

bucket_name = 'hotspotstoplight_floodmapping'
fileNamePrefix = 'data/inputs/'

# export_geotiffs_to_bucket(bucket_name, fileNamePrefix, flood_dates, bbox)

image_collection = read_images_into_collection(bucket_name, fileNamePrefix)


### use the image collection to train a model------------------------------------------------------------

print("Training and assessing model...")

inputProperties = image_collection.first().bandNames().remove('flooded_mask')

# Function to classify and assess each image in the collection
def classify_and_assess(image):

    stratified_sample = image.stratifiedSample(
        numPoints=25000,  # Adjust as needed
        classBand='flooded_mask',
        region=bbox,
        scale=30,
        seed=0
    ).randomColumn()
    
    training_sample = stratified_sample.filter(ee.Filter.lt('random', 0.7))
    testing_sample = stratified_sample.filter(ee.Filter.gte('random', 0.7))
    
    classifier = ee.Classifier.smileRandomForest(10).train(
        features=training_sample,
        classProperty='flooded_mask',
        inputProperties=inputProperties
    )

    classified_image = image.select(inputProperties).classify(classifier)
    
    testAccuracy = testing_sample.classify(classifier).errorMatrix('flooded_mask', 'classification')
    accuracy = testAccuracy.accuracy()
    confusionMatrix = testAccuracy.array()
    
    return ee.Feature(None, {
        'accuracy': accuracy,
        'confusionMatrix': confusionMatrix
    })

# Apply the function over the image collection
assessment_results = image_collection.map(classify_and_assess)

# Convert the assessment results to a list for client-side iteration
# Note: Be cautious with large collections as this might hit memory or computation limits
assessment_results_list = assessment_results.toList(assessment_results.size())

# Fetch the list size (number of images) to the client side
num_results = assessment_results_list.size().getInfo()

print(f'Total images in collection: {num_results}')

# Iterate over each element in the list and print the results
for i in range(num_results):
    # Fetch the result for the current index
    result = ee.Feature(assessment_results_list.get(i)).getInfo()
    
    accuracy = result['properties']['accuracy']
    confusionMatrix = result['properties']['confusionMatrix']
    
    # Print accuracy and confusion matrix for the current image
    print(f'Image {i+1} accuracy:', accuracy)
    print(f'Image {i+1} confusion matrix:', confusionMatrix)



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