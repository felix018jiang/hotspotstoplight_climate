import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.common import initialize_EE, create_folder
from config import (PROJECT_ID, BUCKET_NAME)

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
