import os
import ee
import geemap
from geemap import geojson_to_ee
from datetime import datetime
from data_utils import (
    export_geotiffs_to_bucket,
    export_and_monitor,
    read_images_into_collection,
    train_and_evaluate_classifier,
    make_non_flooding_data,
    process_flood_data
)
from google.cloud import storage

cloud_project = 'hotspotstoplight'
ee.Initialize(project = cloud_project)

file_path = os.path.join(os.path.dirname(__file__), '../../data/inputs/san_jose_aoi/resourceshedbb_CostaRica_SanJose.geojson')
absolute_path = os.path.abspath(file_path)

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