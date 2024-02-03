import os
import json
import ee
import geemap
from geemap import geojson_to_ee, ee_to_geojson
from datetime import datetime, timedelta
from data_utils.make_training_data import make_training_data


### setup------------------------------------------------------------

# initialize
cloud_project = 'hotspotstoplight'
ee.Initialize(project = cloud_project)

# load aoi
file_path = os.path.join(os.path.dirname(__file__), '../../inputs/san_jose_aoi/resourceshedbb_CostaRica_SanJose.geojson')
absolute_path = os.path.abspath(file_path)

with open(absolute_path) as f:
    json_data = json.load(f)

aoi = geojson_to_ee(json_data) # need as a feature collection, not bounding box
bbox = aoi.geometry().bounds()

# load list of dates
flood_dates = [
    # [start_date='2023-09-25', end_date='2023-10-05'], fake dates for the moment
    # [start_date='2023-10-05', end_date='2023-10-15'],
]

# for each date, save training data to data/outputs/training_data
for start_date, end_date in flood_dates:
    geotiff = make_training_data(bbox, start_date, end_date)
    
    # Define the output path
    output_path = f"data/outputs/training_data/output_{start_date}.tif"
    
    # Save the GeoTIFF
    geemap.ee_export_image_to_drive(geotiff, description='output', folder='training_data', file_format='GeoTIFF', filename=output_path)
    
    
    
### model train------------------------------------------------------------
# load all the images from data/outputs/training_data into a single image feature collection in earth engine
directory_path = 'data/outputs/training_data'

# Initialize an empty list to hold the paths of GeoTIFF files
geotiff_paths = []

# Use os.walk to recursively search through the directory for GeoTIFF files
for root, dirs, files in os.walk(directory_path):
    for file in files:
        if file.endswith('.tif') or file.endswith('.tiff'):
            geotiff_paths.append(os.path.join(root, file))

# Convert each asset ID into an ee.Image and store them in a list
image_list = [ee.Image(asset_id) for asset_id in geotiff_paths]

# Create an ee.ImageCollection from the list of ee.Image objects
image_collection = ee.ImageCollection(image_list)

# Get all band names from the combined image
allBandNames = image_collection.bandNames()

# Remove the class band name ('flooded_full_mask') to get input properties
inputProperties = allBandNames.filter(ee.Filter.neq('item', 'flooded_mask'))

# Perform stratified sampling
stratifiedSample = image_collection.stratifiedSample(
    numPoints=25000,  # Total number of points
    classBand='flooded_mask',  # Band to stratify by
    region=bbox,
    scale=30,
    seed=0
).randomColumn()

# Split into training and testing
training = stratifiedSample.filter(ee.Filter.lt('random', 0.7))
testing = stratifiedSample.filter(ee.Filter.gte('random', 0.7))

# Set up the Random Forest classifier for flood prediction
classifier = ee.Classifier.smileRandomForest(10).train(
    features=training,
    classProperty='flooded_mask',  # Use 'flooded_full_mask' as the class property
    inputProperties=inputProperties  # Dynamically generated input properties
)



###  model evaluate------------------------------------------------------------

# Classify the image
classified = image_collection.select(inputProperties).classify(classifier)

# Assess accuracy
testAccuracy = testing.classify(classifier).errorMatrix('flooded_mask', 'classification')

# Calculate accuracy
accuracy = testAccuracy.accuracy().getInfo()

# Convert the confusion matrix to an array
confusionMatrixArray = testAccuracy.array().getInfo()

# Calculate recall for the positive class (assuming '1' represents the positive class for flooding)
true_positives = confusionMatrixArray[1][1]  # True positives
false_negatives = confusionMatrixArray[1][0]  # False negatives
false_positives = confusionMatrixArray[0][1]  # False positives (non-flooded incorrectly identified as flooded)
true_negatives = confusionMatrixArray[0][0]  # True negatives (non-flooded correctly identified as non-flooded)
recall = true_positives / (true_positives + false_negatives)
false_positive_rate = false_positives / (false_positives + true_negatives)

print('Confusion Matrix:', confusionMatrixArray)
print('Accuracy:', accuracy)
print('Recall:', recall)
print('False Positive Rate:', false_positive_rate)



### model predict depending on threshold------------------------------------------------------------
# Set up the Random Forest classifier for flood prediction with probability output
classifier = ee.Classifier.smileRandomForest(10).setOutputMode('PROBABILITY').train(
        features=training,
        classProperty='flooded_mask',
        inputProperties=inputProperties
    )



# Classify the image to get probabilities
probabilityImage = image_collection.select(inputProperties).classify(classifier)



### write results------------------------------------------------------------
geemap.ee_export_image(probabilityImage, filename="costa_rica_flood_probabilities.tif", scale=300, region=aoi)