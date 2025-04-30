"""

This Script Uses a Google Cloud Storage Workflow but does not upload any intermediate steps.
This script will still use Google Earth Engine to create data and the model but will upload results to GCS.
To upload and access data through Google Earth Engine, use the main_ee.py script instead.
To upload and access data through Google Cloud Storage, use the main_gcs.py script instead.
This script will not upload any intermediate steps to GCS.

"""

import ee
from src.setup import setup_gcs
from src.get_roi.get_roi import get_roi
from src.make_study_area.make_study_area import make_study_area
from src.make_training.make_training import make_training
from src.train_model.train_model import train_model
from src.gcs_upload.gcs_upload import check_and_export_geotiff_to_bucket
from config import (DEBUG, BUCKET_NAME, RESOLUTION)



# step 1: Setup GCS and EE
folder_name = setup_gcs(debug=DEBUG)

# step 2: get ROI from URL
roi = get_roi(debug=DEBUG)

# step 3: define the study area
study_area = make_study_area(roi, debug=DEBUG)

# step 4: make the training data
multiband_raster = make_training(study_area, roi, debug=DEBUG)

# step 5: train the model
classified_image, classified_image_asset_name = train_model(multiband_raster, roi, study_area, debug=DEBUG)

# step 6: upload the model to GCS
check_and_export_geotiff_to_bucket(BUCKET_NAME, classified_image_asset_name, classified_image.select(0), RESOLUTION)

