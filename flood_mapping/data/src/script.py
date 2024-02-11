import ee
from data_utils.process_all_data import process_flood_data

cloud_project = 'hotspotstoplight'
ee.Initialize(project = cloud_project)

process_flood_data('Nicaragua')