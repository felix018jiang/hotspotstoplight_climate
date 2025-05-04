from src.make_training.make_training import make_training
from src.ee_upload.ee_upload import export_to_asset
from src.common import asset_exists
import time
import ee
from config import (ROI_NAME, ANALYSIS_YEAR, RESOLUTION)
from src.common import asset_exists
from src.ee_upload.ee_upload import export_to_asset, monitor_task
from src.make_training.make_training import add_bands, viz_training


def make_testing(roi, start_date, end_date, debug=False):
    """
    Creates a multi-band raster for testing the image classification model.

    This function assembles all bands used in training (e.g., climate, vegetation, topography, eco-regions),
    clipped to the full region of interest (ROI) rather than just the training study area. This is necessary
    because the testing area may extend beyond the area used for training. 

    Fire season months are passed in directly and not recalculated here.  They are based on the ROI rather than the training data extent.

    Args:
        roi (ee.FeatureCollection): The region of interest to generate test data over.
        start_date (str): Start date of the fire season (ISO format, e.g., '2021-06-01').
        end_date (str): End date of the fire season (ISO format, e.g., '2021-09-30').
        debug (bool, optional): Whether to print debug messages and display intermediate outputs. Defaults to False.

    Returns:
        ee.Image: A multi-band raster image covering the ROI with all relevant predictor bands and burned area label.
    """


    test_data_asset_name = f"test_data_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"
    if debug:
        print(f"Fire season for {ANALYSIS_YEAR} starts on {start_date}, and ends on {end_date}")
        print("...............................................................................")
    
    ecoregions = ee.FeatureCollection("RESOLVE/ECOREGIONS/2017")
    study_area = ecoregions.filterBounds(roi) # study area is the eco-regions for the roi exactly, no min overlap

    multi_band_raster = add_bands(study_area, study_area, start_date, end_date)
    multi_band_raster = multi_band_raster.reproject(crs='EPSG:4326', scale=RESOLUTION) # nearest-neighbor reproject so even categorical bands are reprojected
    band_names = multi_band_raster.bandNames().getInfo()

    if debug:
        print("Testing MBR Created with the following bands:")
        print(band_names)
        print("...............................................................................")

        viz_training(roi, band_names, multi_band_raster, test_data_asset_name, training=False)

    return multi_band_raster

def make_testing_ee(roi, start_date, end_date, folder_path, debug=False):
    test_data_asset_name = f"test_data_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"
    if not asset_exists(f"{folder_path}/{test_data_asset_name}"):
        if debug:
            print(f"Test data asset {test_data_asset_name} does not exist. Creating it now.")
            print("...............................................................................")
        testing_data = make_testing(roi, start_date, end_date, debug=debug)
        task = export_to_asset(ee_object=testing_data,
                           area=roi.geometry(),
                           folder_path=folder_path,
                           asset_name=test_data_asset_name,
                           scale=RESOLUTION)
        if debug:
            monitor_task(task, test_data_asset_name)
    else:
        testing_data = ee.Image(f"{folder_path}/{test_data_asset_name}")
        if debug:
            print(f"Testing data asset {test_data_asset_name} already exists.")
            print("...............................................................................")
    return testing_data
