"""

This Script Uses a Google Cloud Storage Workflow but does not upload any intermediate steps.
This script will still use Google Earth Engine to create data and the model but will upload results to GCS.
To upload and access data through Google Earth Engine, use the main_ee.py script instead.
This script will not upload any intermediate steps to GCS.

"""

import ee
from src.setup.setup import setup_gcs
from src.get_roi.get_roi import get_roi
from src.make_study_area.make_study_area import make_study_area
from src.make_training.make_training import make_training
from src.make_testing.make_testing import make_testing
from src.train_model.train_model import train_model
from src.test_model.test_model import test_model
from src.mask_water.mask_water import mask_water
from src.gcs_upload.gcs_upload import check_and_export_geotiff_to_bucket
from config import (DEBUG, BUCKET_NAME, RESOLUTION, ROI_NAME, ANALYSIS_YEAR)



# step 1: Setup GCS and EE
folder_name = setup_gcs(debug=DEBUG)


# step 2: get ROI from URL
roi = get_roi(debug=DEBUG)


# step 3: define the study area
study_area = make_study_area(roi, debug=DEBUG)

# # step 4: make the training data
multiband_raster, start_date, end_date = make_training(study_area, roi, debug=DEBUG)

# step 5: make the testing data

testing_data = make_testing(roi, start_date, end_date, debug=DEBUG)

# step 6: train the model
change_classifier = train_model(multiband_raster, study_area, debug=DEBUG)

# step 7: test the model
classified_image = test_model(testing_data, roi, change_classifier, debug=DEBUG)

# step 8:  mask water to low fire probability
water_masked = mask_water(classified_image, testing_data, roi)

water_masked_asset_name = f"classified_image_water_mask_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"

# step 9: upload the model to GCS
check_and_export_geotiff_to_bucket(BUCKET_NAME, water_masked_asset_name, water_masked, RESOLUTION)

