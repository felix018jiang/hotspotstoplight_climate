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
from data_utils.process_all_data import process_flood_data
from google.cloud import storage

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

process_flood_data(absolute_path, date_pairs, 'san jose')