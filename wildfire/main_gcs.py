"""

This Script Uses a Google Cloud Storage Workflow: uploading and accessing all data through GCS Buckets.
This script will still use Google Earth Engine for some operations, but the main workflow is to upload and access all data through Google Cloud Storage.
To upload and access data through Google Earth Engine, use the main_ee.py script instead.

"""

import ee
import geemap
import time
from src.common import initialize_EE, rasterize_ecoregions, create_folder
from src.make_study_area.make_study_area import create_roi_geometry, filter_ecoregions_by_area
from src.get_timeframe.get_timeframe import get_fire_season_months
from src.make_training.make_training import read_and_clip
from config import (PROJECT_ID, ROI_URL, ROI_NAME, MIN_ECOREGION_PCT, 
                    RESOLUTION, SEASON_LENGTH, ANALYSIS_YEAR, 
                    SEASON_REFERENCE_START_YEAR, 
                    SEASON_REFERENCE_END_YEAR, DEBUG, BUCKET_NAME)

from src.common import (
    initialize_EE, create_folder
)

from src.gcs_upload.gcs_upload import check_and_export_geotiff_to_bucket, check_and_export_geojson_to_bucket, file_exists_in_bucket
from src.gcs_download.gcs_download import load_geotiff_from_gcs, load_geojson_from_gcs

# Initialize Earth Engine
initialize_EE(PROJECT_ID)


# Create raw and processed folders for the output assets
raw_folder = f"{ROI_NAME}_Raw"
processed_folder = f"{ROI_NAME}_Processed"

success = create_folder(BUCKET_NAME, raw_folder)
if DEBUG:
    if success:
        print(f"Folder {raw_folder} created in bucket {BUCKET_NAME}.")
    else:
        print(f"Folder {raw_folder} already exists in bucket {BUCKET_NAME}.")
    print("...............................................................................")

success = create_folder(BUCKET_NAME, processed_folder)
if DEBUG:
    if success:
        print(f"Folder {processed_folder} created in bucket {BUCKET_NAME}.")
    else:
        print(f"Folder {processed_folder} already exists in bucket {BUCKET_NAME}.")
    print("...............................................................................")

# Create ROI
roi_asset_name = f"roi_{ROI_NAME}_{RESOLUTION}m"
if not file_exists_in_bucket(BUCKET_NAME, f"{raw_folder}/{roi_asset_name}.geojson"):
    roi = create_roi_geometry(ROI_URL)
    if roi is None:
            raise ValueError("Failed to create ROI geometry. Please check the URL or the response format.")
    if DEBUG:
        print(f"Creating ROI GeoJSON {roi_asset_name} in Bucket {BUCKET_NAME}/{raw_folder}.")
    check_and_export_geojson_to_bucket(BUCKET_NAME, f"{raw_folder}/{roi_asset_name}", roi, RESOLUTION)
else:
    if DEBUG:
        print(f"ROI GeoJSON {roi_asset_name} already exists in {BUCKET_NAME}/{raw_folder}")
    roi = load_geojson_from_gcs(BUCKET_NAME, f"{raw_folder}/{roi_asset_name}.geojson")
    
# Create Study Area
study_area_asset_name = f"study_area_{ROI_NAME}"
if not file_exists_in_bucket(BUCKET_NAME, f"{raw_folder}/{study_area_asset_name}.geojson"):
    
    # Filter Ecoregions by Area
    ecoregions = ee.FeatureCollection("RESOLVE/ECOREGIONS/2017")
    study_area = filter_ecoregions_by_area(ecoregions, roi, MIN_ECOREGION_PCT)
    if DEBUG:
        print(f"Filtered Ecoregions around {ROI_NAME} with minimum area percentage of {MIN_ECOREGION_PCT * 100}%")
        print("...............................................................................")

        # Test the filtered Ecoregions
        Map = geemap.Map()
        Map.centerObject(roi, zoom=6)
        Map.addLayer(study_area, {}, "Filtered Eco-Regions")
        Map.addLayer(roi, {"color": "red"}, 'ROI')
        eco_regions_filename = f"{ROI_NAME}_study_area"
        Map.to_html('scratch/test_outputs/' + eco_regions_filename + '.html')
   
        print(f"Study Area Test Map saved as test_outputs/{eco_regions_filename}.html")
        print("...............................................................................")
    
        # Pause execution to take a command line input
        user_input = input("Does the Study Area Map Look Correct? (Y/N): ").strip().upper()

        if user_input == 'N':
            print("Exiting the program. Please check the map and try again.")
            exit()
        elif user_input != 'Y':
            raise ValueError("Invalid input. Please enter 'Y' to continue or 'N' to quit.")
        print("...............................................................................")

    # Export the filtered ecoregions to an asset

    check_and_export_geojson_to_bucket(BUCKET_NAME, f"{raw_folder}/{study_area_asset_name}", study_area, RESOLUTION)
    if DEBUG:
        print(f"Export task for {study_area_asset_name} started.")
        print("...............................................................................")

else:
    if DEBUG:
        print(f"{ROI_NAME} Study Area Asset already exists.")
    study_area = load_geojson_from_gcs(BUCKET_NAME, f"{raw_folder}/{study_area_asset_name}.geojson")
if DEBUG:
    print("...............................................................................")