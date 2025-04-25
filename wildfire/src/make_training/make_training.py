import os
import sys
import ee
import geemap
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import (ROI_NAME, SEASON_LENGTH, ANALYSIS_YEAR,
                    SEASON_REFERENCE_START_YEAR, SEASON_REFERENCE_END_YEAR,
                    RESOLUTION)
from src.get_timeframe.get_timeframe import get_fire_season_months
from src.common import rasterize_ecoregions


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

def make_training(study_area, roi, debug=False):
    # Get Study Timeframe
    start_date, end_date, fire_months = get_fire_season_months(study_area, SEASON_REFERENCE_START_YEAR, 
                                    SEASON_REFERENCE_END_YEAR, ANALYSIS_YEAR, SEASON_LENGTH)
    if debug:
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

    if debug:
        print("Training Data MBR Created with the following bands:")
        print(band_names)
        print("...............................................................................")

        viz_training(roi, band_names, multi_band_raster, training_data_asset_name)
    return multi_band_raster



def viz_training(roi, band_names, multi_band_raster, training_data_asset_name):
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