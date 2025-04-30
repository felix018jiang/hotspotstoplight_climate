import os
import sys
import ee
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.gcs_upload.gcs_upload import check_and_export_geojson_to_bucket, file_exists_in_bucket
from src.make_study_area.make_study_area import create_roi_geometry
from src.gcs_download.gcs_download import load_geotiff_from_gcs, load_geojson_from_gcs

from config import (ROI_URL, ROI_NAME,
                    RESOLUTION, PROJECT_ID)


def get_roi(debug= False):
    roi_asset_name = f"roi_{ROI_NAME}_{RESOLUTION}m"
    folder_path = f'projects/{PROJECT_ID}/assets/{ROI_NAME}'
    roi = create_roi_geometry(ROI_URL) # returns EE geometry
    if roi is None:
        if debug:
            print(f"Failed to create ROI geometry from {ROI_URL}.")
            print("Retrying.........")
        return get_roi(debug=debug)
        #roi = ee.FeatureCollection(f"{folder_path}/{roi_asset_name}")
        #raise ValueError("Failed to create ROI geometry. Please check the URL or the response format.")
    else:
        if debug:
            print(f"ROI GeoJSON {roi_asset_name} successfully created.")
    return roi