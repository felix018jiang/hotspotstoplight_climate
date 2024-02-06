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

n = image_collection.size().getInfo()
samples_per_image = 100000 // n 

def aggregate_samples(image, numPoints):
    return image.stratifiedSample(
        numPoints=numPoints,
        classBand='flooded_mask',
        region=bbox,
        scale=30,
        seed=0
    ).randomColumn()


all_samples = image_collection.map(lambda image: aggregate_samples(image, samples_per_image)).flatten()


# Split the aggregated samples into training and testing sets
training_samples = all_samples.filter(ee.Filter.lt('random', 0.7))
testing_samples = all_samples.filter(ee.Filter.gte('random', 0.7))

# Train one classifier on the aggregated training samples
classifier = ee.Classifier.smileRandomForest(10).train(
    features=training_samples,
    classProperty='flooded_mask',
    inputProperties=inputProperties
)

# Function to classify an image using the trained classifier
def classify_image(image):
    return image.select(inputProperties).classify(classifier)

# Classify all images in the collection using the trained classifier
classified_images = image_collection.map(classify_image)

# Evaluate the classifier's performance using the testing set
testAccuracy = testing_samples.classify(classifier).errorMatrix('flooded_mask', 'classification')
accuracy = testAccuracy.accuracy().getInfo()
confusionMatrix = testAccuracy.array().getInfo()

# Extract elements from the confusion matrix for calculations
true_positives = confusionMatrix[1][1]  # True positives
false_negatives = confusionMatrix[1][0]  # False negatives
false_positives = confusionMatrix[0][1]  # False positives (non-flooded incorrectly identified as flooded)
true_negatives = confusionMatrix[0][0]  # True negatives (non-flooded correctly identified as non-flooded)

# Calculate recall and false positive rate
recall = true_positives / (true_positives + false_negatives)
false_positive_rate = false_positives / (false_positives + true_negatives)

# Prepare the final assessment result with additional metrics
final_assessment_result = {
    'accuracy': accuracy,
    'confusionMatrix': confusionMatrix,
    'true_positives': true_positives,
    'false_negatives': false_negatives,
    'false_positives': false_positives,
    'true_negatives': true_negatives,
    'recall': recall,
    'false_positive_rate': false_positive_rate
}

# Print the metrics
print('Confusion Matrix:', confusionMatrix)
print('Accuracy:', accuracy)
print('Recall:', recall)
print('False Positive Rate:', false_positive_rate)


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