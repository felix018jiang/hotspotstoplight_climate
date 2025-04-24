import os
import sys
import ee

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import (PROJECT_ID, ROI_URL, ROI_NAME, MIN_ECOREGION_PCT, 
                    RESOLUTION, SEASON_LENGTH, ANALYSIS_YEAR, 
                    SEASON_REFERENCE_START_YEAR, 
                    SEASON_REFERENCE_END_YEAR, DEBUG, BUCKET_NAME)


from src.common import (
    initialize_EE, check_and_export_geotiff_to_bucket,
    create_folder, check_and_export_geojson_to_bucket
)

initialize_EE(PROJECT_ID)

roi_asset_name = f"roi_{ROI_NAME}_{RESOLUTION}m"
folder_path = f'projects/{PROJECT_ID}/assets/{ROI_NAME}'

roi = ee.FeatureCollection(f"{folder_path}/{roi_asset_name}")
raw_folder = f"{ROI_NAME}_Raw"
processed_folder = f"{ROI_NAME}_Processed"

#create_folder(BUCKET_NAME, raw_folder)
#create_folder(BUCKET_NAME, processed_folder)

check_and_export_geojson_to_bucket(BUCKET_NAME, f"{raw_folder}/{roi_asset_name}", roi, RESOLUTION)

training_data_asset_name = f"training_data_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"
training_data = ee.Image(f"{folder_path}/{training_data_asset_name}")

#print(training_data.getInfo())
# Check if the training data exists in the bucket       

check_and_export_geotiff_to_bucket(
    BUCKET_NAME, f"{processed_folder}/{training_data_asset_name}", training_data, RESOLUTION
)
