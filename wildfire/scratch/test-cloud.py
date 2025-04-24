import os
import sys
import ee



sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#from src.get_timeframe.get_timeframe import get_fire_season_months
from src.gcs_upload.gcs_upload import file_exists_in_bucket

from config import (PROJECT_ID, ROI_URL, ROI_NAME, MIN_ECOREGION_PCT, 
                    RESOLUTION, SEASON_LENGTH, ANALYSIS_YEAR, 
                    SEASON_REFERENCE_START_YEAR, 
                    SEASON_REFERENCE_END_YEAR, DEBUG, BUCKET_NAME)


from src.common import (
    initialize_EE, create_folder
)



initialize_EE(PROJECT_ID)

# roi = ee.FeatureCollection("gs://musa-wildfire-private/Angola_Raw/roi_Angola_30m.geojson")

tif = ee.Image.loadGeoTIFF("gs://musa-wildfire-private/Angola_Processed/training_data_Angola_2020_30m0000033024-0000022016.tif")
print(tif.getInfo())
# print(roi.getInfo())

# roi_asset_name = f"roi_{ROI_NAME}_{RESOLUTION}m"
# folder_path = f'projects/{PROJECT_ID}/assets/{ROI_NAME}'

# roi = ee.FeatureCollection(f"{folder_path}/{roi_asset_name}")
# raw_folder = f"{ROI_NAME}_Raw"
# processed_folder = f"{ROI_NAME}_Processed"

# print(create_folder(BUCKET_NAME, raw_folder))
# print(create_folder(BUCKET_NAME, processed_folder))

# # check_and_export_geojson_to_bucket(BUCKET_NAME, f"{raw_folder}/{roi_asset_name}", roi, RESOLUTION)

# # training_data_asset_name = f"training_data_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"
# # training_data = ee.Image(f"{folder_path}/{training_data_asset_name}")g

# # #print(training_data.getInfo())
# # # Check if the training data exists in the bucket       

# # check_and_export_geotiff_to_bucket(
# #     BUCKET_NAME, f"{processed_folder}/{training_data_asset_name}", training_data, RESOLUTION
# # )

# # preds = ee.Image("projects/musa-wildfire-449918/assets/Angola/classified_image_30m")

# # preds_asset_name = f"predictions_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"
# # check_and_export_geotiff_to_bucket(
# #     BUCKET_NAME, f"{processed_folder}/{preds_asset_name}", preds, RESOLUTION
# # )
