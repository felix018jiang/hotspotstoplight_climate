import os
import sys
import ee
import geemap
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import (ROI_NAME, SEASON_LENGTH, ANALYSIS_YEAR,
                    SEASON_REFERENCE_START_YEAR, SEASON_REFERENCE_END_YEAR,
                    RESOLUTION)
from src.get_timeframe.get_timeframe import get_fire_season_months
from src.common import rasterize_ecoregions, asset_exists
from src.ee_upload.ee_upload import export_to_asset
import time


def read_and_clip(id, area, band, start= None, end= None):
    if start is not None and end is not None:
        band = ee.ImageCollection(id) \
            .filter(ee.Filter.date(start, end)) \
            .select(band) \
            .mean() \
            .clip(area)
    else: # for layers that don't have a date range like AGB
        band = ee.ImageCollection(id) \
            .select(band) \
            .mean() \
            .clip(area)
    return band

def make_training(study_area, roi, start_date, end_date, debug=False):
    print(start_date, end_date)
    if start_date is None or end_date is None:
        print("either date are None")
        
        # Get Study Timeframe
        start_date, end_date, fire_months = get_fire_season_months(study_area, SEASON_REFERENCE_START_YEAR, 
                                        SEASON_REFERENCE_END_YEAR, ANALYSIS_YEAR, SEASON_LENGTH)
        print('after assigning start and end date')
        print(f"Start Date: {start_date}, End Date: {end_date}")
        if debug:
            print(f"Fire season months for {ANALYSIS_YEAR} are: {fire_months}")
            print("...............................................................................")

    training_data_asset_name = f"training_data_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"

    bands_to_export = [
    {"code": "IDAHO_EPSCOR/TERRACLIMATE", "bands": ["pdsi", "tmmx", "vs", "soil", "pr"], "time": True},
    {"code": "NASA/ORNL/biomass_carbon_density/v1", "bands": ["agb"], "time": False},
    {"code": "projects/musa-wildfire-449918/assets/rasterized_ecoregions_full_30m_unclipped", "bands": [], "time": False},
    {"code": "NASA/NASADEM_HGT/001", "bands": ["elevation", "swb"], "time": False}  #,
    #{"code": "MODIS/061/MCD64A1", "bands": ["BurnDate"], "time": True}, # bilinear resamping is taking away the few burn dates
    ]

    study_area_img = rasterize_ecoregions(study_area, RESOLUTION)
    multi_band_raster = study_area_img

    # Combine Training Data into One Multi-Band Raster
    multi_band_raster = multi_band_raster.select(['first']).rename(['eco-regions'])
    for dataset in bands_to_export:
        if dataset["time"]:
            for band in dataset["bands"]:
                lyr = read_and_clip(dataset['code'], study_area, band, start_date, end_date)
                newProj = lyr.projection().atScale(RESOLUTION) # resample to 30m all bands
                lyr = lyr.resample('bilinear').reproject(newProj)
                multi_band_raster = multi_band_raster.addBands([lyr])
    dem = ee.Image('NASA/NASADEM_HGT/001').select('elevation').updateMask(study_area_img)
    multi_band_raster = multi_band_raster.addBands([dem])
    agb = read_and_clip('NASA/ORNL/biomass_carbon_density/v1', study_area, 'agb')
    multi_band_raster = multi_band_raster.addBands([agb])
    BurnDate = read_and_clip("MODIS/061/MCD64A1", study_area, "BurnDate")
    multi_band_raster= multi_band_raster.addBands([BurnDate])

    multi_band_raster = make_burned_binary(multi_band_raster, roi, study_area, debug=debug)

    band_names = multi_band_raster.bandNames().getInfo()

    if debug:
        print("MBR Created with the following bands:")
        print(band_names)
        print("...............................................................................")

        viz_training(roi, band_names, multi_band_raster, training_data_asset_name)
    return multi_band_raster, start_date, end_date



def viz_training(roi, band_names, multi_band_raster, training_data_asset_name):
    Map = geemap.Map()
    Map.centerObject(roi, zoom=6)
    # Loop through bands and add to map
    visParams = {
        "eco-regions": {"min": 450, "max": 506, "palette": ['f7fcf0', '00441b']},
        "pdsi": {"min": -800, "max": 800, "palette": ['red', 'white', 'blue']},
        "tmmx": {"min": 117, "max": 352, "palette": ['blue', 'green', 'red']},
        "vs": {"min": 0, "max": 533, "palette": ['white', 'purple']},
        "soil": {"min": 0, "max": 3000, "palette": ['#ffffcc', '#41b6c4', '#0c2c84']},
        "pr": {"min": 0, "max": 275, "palette": ['white', 'lightblue', 'blue']},
        "BurnDate": {"min": 0, "max": 366, "palette": ['yellow', 'orange', 'red']},
        "elevation": {"min": 0, "max": 3658, "palette": ['white', 'brown']},
        "agb": {"min": 0, "max": 180, "palette": ['white', 'green', 'darkgreen']},
        "is_burned": {"min": 0, "max": 1, "palette": ['white', 'red']}
    }

    # Loop through bands and add them as layers
    for band_name in band_names:
        vis = visParams.get(band_name, {"min": 0, "max": 1})
        layer = multi_band_raster.select(band_name)
        Map.addLayer(layer, vis, band_name)
    Map.addLayer(roi, {}, "ROI")
    Map.to_html(f'scratch/test_outputs/{training_data_asset_name}.html')
    print(f"Multi-Band Raster Training Data saved as scratch/test_outputs/{training_data_asset_name}.html")
    print("...............................................................................")

    # Pause execution to take a command line input
    user_input = input("Does the Training Data Map Look Correct? (Y/N): ").strip().upper()

    if user_input == 'N':
        print("Exiting the program. Please check the map and try again.")
        exit()
    elif user_input != 'Y':
        print("Invalid input. Please enter 'Y' to continue or 'N' to quit.")
        viz_training(roi, band_names, multi_band_raster, training_data_asset_name)


def make_training_ee(study_area, roi, start_date, end_date, folder_path, debug=False):
    training_data_asset_name = f"training_data_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"
    if not asset_exists(f"{folder_path}/{training_data_asset_name}"):
        if debug:
            print(f"Training data asset {training_data_asset_name} does not exist. Creating it now.")
            print("...............................................................................")
        multi_band_raster, sd, ed = make_training(study_area, roi, start_date, end_date, debug=debug)
        task = export_to_asset(ee_object=multi_band_raster,
                           area=study_area.geometry(),
                           folder_path=folder_path,
                           asset_name=training_data_asset_name,
                           scale=RESOLUTION)
        if debug:
            print(f"Export task for {training_data_asset_name} started. Check the Earth Engine Code Editor for progress.")
            print("...............................................................................")

            while task.active():
                print(f"Exporting {training_data_asset_name}...")
                time.sleep(20)
            print("Done!")
    else:
        multi_band_raster = ee.Image(f"{folder_path}/{training_data_asset_name}")
        if debug:
            print(f"Training data asset {training_data_asset_name} already exists.")
            print("...............................................................................")
    return multi_band_raster, start_date, end_date

def make_burned_binary(multiband_raster, roi, study_area, debug=False):
    # unmask non-burned areas and set to 0, then convert burn_date to a binary where unburned is 0, burned is 1
    binary_burned = multiband_raster.select("BurnDate").rename("is_burned").unmask(0).gt(0)  
    multiband_raster = multiband_raster.addBands(binary_burned)
    
    # Print the count of each value in the "is_burned" band
    value_counts = binary_burned.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=roi.geometry(),
        scale=RESOLUTION,
        maxPixels=1e13
    ).get("is_burned")
    
    value_counts_dict = value_counts.getInfo()
    if value_counts_dict:
        for value, count in value_counts_dict.items():
            print(f"Value {value}: {count}")
    else:
        print("No values found in the 'is_burned' band.")
    if debug:
        print("Burned binary band created")
        print("...............................................................................")
    return multiband_raster.clip(study_area)  # Clip to study area to remove any artifacts outside the ROI