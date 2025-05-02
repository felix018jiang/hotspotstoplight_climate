from src.make_training.make_training import make_training
from src.ee_upload.ee_upload import export_to_asset
from src.common import asset_exists
import time
import ee

from config import (
    ANALYSIS_YEAR, RESOLUTION, ROI_NAME
)


def make_testing(roi, start_date, end_date, debug=False):
    """
    This function is used to create a testing dataset for the model.
    This will include all of the bands used in the training dataset, just clipped to the ROI rather than the study area.
    There are some cases where the ROI will include areas outside of the study area, which is why we can't just clip the trainging dataset.
    Fire season months are not recalculated here, they are passed in from the training data creation and based on data of the whole fire area. 
    TODO: if training exists but testing doesn't fire season months are recalculated when they shouldn't be.
    """
    print(start_date, end_date)
    testing_data = make_training(roi, roi, start_date, end_date, debug=debug)

    return testing_data

def make_testing_ee(roi, start_date, end_date, folder_path, debug=False):
    print('we in make testing')
    print(start_date, end_date)
    testing_data_asset_name = f"testing_data_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"
    if not asset_exists(f"{folder_path}/{testing_data_asset_name}"):
        print("testing asset DNE")
        if debug:
            print(f"Testing data asset {testing_data_asset_name} does not exist. Creating it now.")
            print("...............................................................................")
        print("Creating testing data...")
        testing_data = make_testing(roi, start_date, end_date, debug=debug)
        task = export_to_asset(ee_object=testing_data,
                           area=roi.geometry(),
                           folder_path=folder_path,
                           asset_name=testing_data_asset_name,
                           scale=RESOLUTION)
        if debug:
            print(f"Export task for {testing_data_asset_name} started. Check the Earth Engine Code Editor for progress.")
            print("...............................................................................")

            while task.active():
                print(f"Exporting {testing_data_asset_name}...")
                time.sleep(20)
            print("Done!")
    else:
        testing_data = ee.Image(f"{folder_path}/{testing_data_asset_name}")
        if debug:
            print(f"Testing data asset {testing_data_asset_name} already exists.")
            print("...............................................................................")
    return testing_data
