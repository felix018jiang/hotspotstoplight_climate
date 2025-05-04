import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import ee
import requests
import requests
import geemap
import time

from src.common import asset_exists
from src.ee_upload.ee_upload import export_to_asset, monitor_task
from config import (ROI_NAME, MIN_ECOREGION_PCT)


def filter_ecoregions_by_area(ecoregions, roi, min_percentage=0.05):
    """Filter ecoregions by area coverage within ROI. 
    Only Retain Eco-Regions that make up at least {min_percentage} of the ROI"""

    return ecoregions.map(lambda eco_region: eco_region.set(
        'intersection_area_percentage',
        eco_region.geometry().intersection(roi.geometry()).area().divide(roi.geometry().area())
    )).filter(ee.Filter.gte('intersection_area_percentage', min_percentage))

def visualize_ecoregions(study_area, roi):
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
        print("Invalid input. Please enter 'Y' to continue or 'N' to quit.")
        visualize_ecoregions(study_area, roi)

def make_study_area(roi, debug=False):
    
    # Filter Ecoregions by Area
    ecoregions = ee.FeatureCollection("RESOLVE/ECOREGIONS/2017")
    study_area = filter_ecoregions_by_area(ecoregions, roi, MIN_ECOREGION_PCT)
    if debug:
        print(f"Filtered Ecoregions around {ROI_NAME} with minimum area percentage of {MIN_ECOREGION_PCT * 100}%")
        print("...............................................................................")
        # Test the filtered Ecoregions
        visualize_ecoregions(study_area, roi)
    return study_area

def make_study_area_ee(roi, folder_path, debug=False):
    """
    This function retrieves the study area from EE if it exits, otherwise it creates a new study area.
    """

    study_area_asset_name = f"study_area_{ROI_NAME}"

    if not asset_exists(f"{folder_path}/{study_area_asset_name}"):
        study_area = make_study_area(roi, debug=debug)
            
        task = export_to_asset(ee_object=study_area,
                        area=study_area.geometry(),
                        folder_path=folder_path,
                        asset_name=study_area_asset_name)
        
        if debug:
            print(f"Export task for {study_area_asset_name} started. Check the Earth Engine Code Editor for progress.")
            print("...............................................................................")

            monitor_task(task, study_area_asset_name)
    else:
        study_area = ee.FeatureCollection(f"{folder_path}/{study_area_asset_name}")
        if debug:
            print(f"Study area {study_area_asset_name} already exists. Loading from asset.")
            print("...............................................................................")
    return study_area
