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
import pandas as pd

cloud_project = 'hotspotstoplight'
ee.Initialize(project = cloud_project)

df = pd.read_excel('/home/nissim/Documents/dev/Climate/flood_mapping/data/inputs/argentina_flood_dates/public_emdat_custom_request_2024-02-09_092341d2-99a8-4dea-95aa-7cb0984cb9e9.xlsx')
df['start_date'] = pd.to_datetime({'year': df['Start Year'], 'month': df['Start Month'], 'day': df['Start Day']})
df['end_date'] = pd.to_datetime({'year': df['End Year'], 'month': df['End Month'], 'day': df['End Day']})
date_pairs = [(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) for start_date, end_date in zip(df['start_date'], df['end_date'])]

process_flood_data('costa rica', date_pairs)