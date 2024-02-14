import ee
from data_utils.process_all_data import process_flood_data

cloud_project = 'hotspotstoplight'
ee.Initialize(project=cloud_project)

# only runs for countries for the moment
place_names = ['Uruguay']

for place_name in place_names:

    print("Processing data for", place_name, "...")

    process_flood_data(place_name)
