"""

This Script Uses an Earth Engine Workflow: uploading and accessing all data through Google Earth Engine.
To upload and access data through Google Cloud Storage, use the main_gcs.py script instead.

"""

import ee
import geemap
import time
from src.common import initialize_EE, export_to_asset, asset_exists, rasterize_ecoregions
from src.make_study_area.make_study_area import create_roi_geometry, filter_ecoregions_by_area
from src.get_timeframe.get_timeframe import get_fire_season_months
from src.make_training.make_training import read_and_clip
from config import (PROJECT_ID, ROI_URL, ROI_NAME, MIN_ECOREGION_PCT, 
                    RESOLUTION, SEASON_LENGTH, ANALYSIS_YEAR, 
                    SEASON_REFERENCE_START_YEAR, 
                    SEASON_REFERENCE_END_YEAR, DEBUG)

# Initialize Earth Engine
initialize_EE(PROJECT_ID)


# Create a folder for the output assets
folder_path = f'projects/{PROJECT_ID}/assets/{ROI_NAME}'
if not asset_exists(folder_path):
    if DEBUG:
        print(f"Creating folder {folder_path} in GEE assets.")
        print("...............................................................................")
    ee.data.createAsset({'type': 'FOLDER'}, folder_path)

# Create ROI
roi_asset_name = f"roi_{ROI_NAME}_{RESOLUTION}m"
if not asset_exists(f"{folder_path}/{roi_asset_name}"):
    roi = create_roi_geometry(ROI_URL)
    if roi is None:
        raise ValueError("Failed to create ROI geometry. Please check the URL or the response format.")
    if DEBUG:
        print(f"Creating ROI asset {roi_asset_name} in GEE assets.")
    export_to_asset(ee_object=roi,
                    area=roi.geometry(),
                    folder_path=folder_path,
                    asset_name=roi_asset_name)
else:
    roi = ee.FeatureCollection(f"{folder_path}/{roi_asset_name}")


if DEBUG:
    print("...............................................................................")

# Create Study Area
study_area_asset_name = f"study_area_{ROI_NAME}"
if not asset_exists(f"{folder_path}/{study_area_asset_name}"):
    
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
    task = export_to_asset(ee_object=study_area,
                            area=study_area,
                            folder_path=folder_path,
                            asset_name=study_area_asset_name)
    if DEBUG:
        print(f"Export task for {study_area_asset_name} started. Check the Earth Engine Code Editor for progress.")
        print("...............................................................................")

    if DEBUG:
        while task.active():
        
            print(f"Exporting {study_area_asset_name}...")
            time.sleep(20)

        print("Done!")

else:
    if DEBUG:
        print(f"{ROI_NAME} Study Area Asset already exists.")
    study_area = ee.FeatureCollection(f"{folder_path}/{study_area_asset_name}")
if DEBUG:
    print("...............................................................................")

# Get Study Timeframe
start_date, end_date, fire_months = get_fire_season_months(study_area, SEASON_REFERENCE_START_YEAR, 
                                    SEASON_REFERENCE_END_YEAR, ANALYSIS_YEAR, SEASON_LENGTH)
if DEBUG:
    print(f"Fire season months for {ANALYSIS_YEAR} are: {fire_months}")
    print("...............................................................................")

training_data_asset_name = f"training_data_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"

bands_to_export = [
    {"code": "IDAHO_EPSCOR/TERRACLIMATE", "bands": ["pdsi", "tmmx", "vs", "soil", "pr"], "time": True},
    {"code": "NASA/ORNL/biomass_carbon_density/v1", "bands": ["agb"], "time": False},
    {"code": "projects/musa-wildfire-449918/assets/rasterized_ecoregions_full_30m_unclipped", "bands": [], "time": False},
    {"code": "NASA/NASADEM_HGT/001", "bands": ["elevation", "swb"], "time": False},
    {"code": "MODIS/061/MCD64A1", "bands": ["BurnDate"], "time": True},
]

if asset_exists(f"{folder_path}/{training_data_asset_name}"):
    if DEBUG:
        print(f"Training data asset {training_data_asset_name} already exists.")
        print("...............................................................................")
else:
    if DEBUG:
        print(f"Creating training data asset {training_data_asset_name} in GEE assets.")
        print("...............................................................................")
    study_area_img = rasterize_ecoregions(study_area, RESOLUTION)
    multi_band_raster = study_area_img

    # Combine Training Data into One Multi-Band Raster
    multi_band_raster = multi_band_raster.select(['first']).rename(['eco-regions'])
    for dataset in bands_to_export:
        if dataset["time"]:
            for band in dataset["bands"]:
                lyr = read_and_clip(dataset['code'], study_area, band, start_date, end_date)
                multi_band_raster = multi_band_raster.addBands([lyr])
    dem = ee.Image('NASA/NASADEM_HGT/001').select('elevation').updateMask(study_area_img)
    multi_band_raster = multi_band_raster.addBands([dem])
    agb = read_and_clip('NASA/ORNL/biomass_carbon_density/v1', study_area, 'agb')
    multi_band_raster = multi_band_raster.addBands([agb])
    band_names = multi_band_raster.bandNames().getInfo()

    if DEBUG:
        print("Training Data MBR Created with the following bands:")
        print(band_names)
        print("...............................................................................")

        # Test the Multi-Band Raster
        Map = geemap.Map()
        Map.centerObject(roi, zoom=6)
        # Loop through bands and add to map
        for band in band_names:
            band_img = multi_band_raster.select(band)

            vis_params = {"min": 0, "max": 1, "palette": ["white", "blue", "green", "red"]}
            Map.addLayer(band_img, vis_params, band)
            Map.addLayer(roi, {}, 'ROI')

        Map.addLayerControl()
        Map.to_html(f'scratch/test_outputs/{training_data_asset_name}.html')
        print(f"Multi-Band Raster Test Map saved as scratch/test_outputs/{training_data_asset_name}.html")
        print("...............................................................................")

        # Pause execution to take a command line input
        user_input = input("Does the Training Data Map Look Correct? (Y/N): ").strip().upper()

        if user_input == 'N':
            print("Exiting the program. Please check the map and try again.")
            exit()
        elif user_input != 'Y':
            raise ValueError("Invalid input. Please enter 'Y' to continue or 'N' to quit.")
        print("...............................................................................")

    # Export the Multi-Band Raster to an asset
    task = export_to_asset(ee_object=multi_band_raster,
                           area=study_area.geometry(),
                           folder_path=folder_path,
                           asset_name=training_data_asset_name,
                           scale=RESOLUTION)
    
    if DEBUG:
        print(f"Export task for {training_data_asset_name} started. Check the Earth Engine Code Editor for progress.")
        print("...............................................................................")

        while task.active():
            print(f"Exporting {training_data_asset_name}...")
            time.sleep(20)

        print("Done!")
    print("...............................................................................")
