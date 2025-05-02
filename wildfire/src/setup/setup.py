import os
import sys
import ee
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.common import initialize_EE, create_folder
from src.common import asset_exists
from config import (PROJECT_ID, BUCKET_NAME, ROI_NAME)

def setup_gcs(debug=False):

    # Initialize Earth Engine
    initialize_EE(PROJECT_ID)

    # Create performance_metrics folder for the output assets
    p_folder = "performance_metrics"

    success = create_folder(BUCKET_NAME, p_folder)
    if debug:
        if success:
            print(f"Folder {p_folder} created in bucket {BUCKET_NAME}.")
        else:
            print(f"Folder {p_folder} already exists in bucket {BUCKET_NAME}.")
        print("...............................................................................")
    return p_folder

def setup_ee(debug=False):
    # Initialize Earth Engine
    initialize_EE(PROJECT_ID)

    if debug:
        print("Earth Engine initialized successfully.")
        print("...............................................................................")
    folder_path = f'projects/{PROJECT_ID}/assets/{ROI_NAME}'
    if not asset_exists(folder_path):
        ee.data.createAsset({'type': 'FOLDER'}, folder_path)
        if debug:
            print(f"Created folder {folder_path} in GEE assets.")
            print("...............................................................................")
    return folder_path    