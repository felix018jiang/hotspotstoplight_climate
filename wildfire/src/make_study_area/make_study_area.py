import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import ee
import requests
import requests
import geemap

from config import (ROI_NAME, MIN_ECOREGION_PCT)


def create_roi_geometry(url):
    """Create a region of interest geometry from a GeoJSON URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        geojson = requests.get(url).json()

        # Extract geometry and convert to Earth Engine geometry
        geometry = ee.Geometry(geojson["features"][0]["geometry"])

        # Wrap geometry in a FeatureCollection
        feature_collection = ee.FeatureCollection([ee.Feature(geometry)])

        return feature_collection

    except (requests.RequestException, KeyError, IndexError, ee.EEException) as e:
        print(f"Error creating ROI geometry: {e}")
        return None


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
        raise ValueError("Invalid input. Please enter 'Y' to continue or 'N' to quit.")
    print("...............................................................................")

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
