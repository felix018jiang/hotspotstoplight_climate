import os
import json
import time
import ee
import geemap
from geemap import geojson_to_ee
from datetime import datetime
from data_utils.write_to_cloud import export_geotiffs_to_bucket
from data_utils.export_and_monitor import export_and_monitor
from data_utils.read_from_cloud import read_images_into_collection
from data_utils.train_and_eval import train_and_evaluate_classifier
from data_utils.make_data_to_classify import make_non_flooding_data
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
    # ('2016-11-24', '2016-11-26'), EEException: Image.gt: If one image has no bands, the other must also have no bands. Got 0 and 1.
    # ('2015-10-27', '2015-10-29'), ""
    # ('2015-07-06', '2015-07-08'), ""
    ('2021-07-22', '2021-07-28'),
    ('2018-10-02', '2018-10-11')
]

flood_dates = [(datetime.strptime(start, '%Y-%m-%d').date(), datetime.strptime(end, '%Y-%m-%d').date()) for start, end in date_pairs]



### create data, write to cloud bucket, read in as image collection------------------------------------------------------------

bucket_name = 'hotspotstoplight_floodmapping'
fileNamePrefix = 'data/inputs/'

export_geotiffs_to_bucket(bucket_name, fileNamePrefix, flood_dates, bbox)

image_collection = read_images_into_collection(bucket_name, fileNamePrefix)


### use the image collection to train a model------------------------------------------------------------

print("Training and assessing model...")

inputProperties, training = train_and_evaluate_classifier(image_collection, bbox)

### make final image to classify probability, write results---------------------------------------------------------------

final_image = make_non_flooding_data(bbox)

classifier = ee.Classifier.smileRandomForest(10).setOutputMode('PROBABILITY').train(
    features=training,
    classProperty='flooded_mask',
    inputProperties=inputProperties
)
probabilityImage = final_image.classify(classifier)

floodProbFileNamePrefix = 'data/outputs/costa_rica_san_jose_flood_prob'
export_and_monitor(probabilityImage, "Flood probability", bucket_name, floodProbFileNamePrefix, scale=30)