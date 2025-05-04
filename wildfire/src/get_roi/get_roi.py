import os
import sys
import ee
import requests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.gcs_upload.gcs_upload import check_and_export_geojson_to_bucket, file_exists_in_bucket
from src.gcs_download.gcs_download import load_geotiff_from_gcs, load_geojson_from_gcs
from src.ee_upload.ee_upload import export_to_asset, monitor_task
from src.common import asset_exists


from config import (ROI_URL, ROI_NAME,
                    RESOLUTION, PROJECT_ID)


def create_roi_geometry(url, debug= False):
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
        if debug:
            print(f"Error creating ROI geometry: {e}")
        return None


def get_roi(debug= False):
    roi_asset_name = f"roi_{ROI_NAME}_{RESOLUTION}m"
    #folder_path = f'projects/{PROJECT_ID}/assets/{ROI_NAME}'
    roi = create_roi_geometry(ROI_URL, debug) # returns EE geometry
    retries = 0

    if roi is None:
        if debug:
            print("Retrying.........")
        retries += 1
        if retries > 100:
            raise ValueError("Failed to create ROI geometry after multiple attempts.")
        return get_roi(debug=debug)
    else:
        if debug:
            print(f"ROI GeoJSON {roi_asset_name} successfully created.")
    return roi

def get_roi_ee(folder_path, debug=False):
    """
    This function retrieves the ROI from the specified URL and returns it as an Earth Engine geometry object.
    If the ROI is not found, it retries until successful.
    """
    roi_asset_name = f"roi_{ROI_NAME}_{RESOLUTION}m"
    
    if not asset_exists(f"{folder_path}/{roi_asset_name}"):
        roi = get_roi()
        print(f"ROI Asset saved to {folder_path}/{roi_asset_name}")
        print("...............................................................................")
        task = export_to_asset(ee_object=roi,
                    area=roi.geometry(),
                    folder_path=folder_path,
                    asset_name=roi_asset_name)
        if debug:
            monitor_task(task, roi_asset_name)
    else:
        if debug:
            print(f"ROI Asset already exists in {folder_path}/{roi_asset_name}.")
        roi = ee.FeatureCollection(f"{folder_path}/{roi_asset_name}")
        if debug:
            print("Loaded ROI from EE")
            print("...............................................................................")
        
    return roi
