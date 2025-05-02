import geemap
import ee
from config import (
    EXPLANATORY_VARS, RESOLUTION, ROI_NAME,
    ANALYSIS_YEAR
)
from src.validate_model.validate_model import plot_roc_curve
from src.train_model.train_model import sample_data
from src.common import asset_exists
from src.ee_upload.ee_upload import export_to_asset

def predict_model(testing_data, change_classifier, debug = False):
    """
    This function will generate predictions for the model using the test dataset.
    The output will be a classified image, where each pixel represents the probability of being burned.
    """
    classified_image = testing_data.select(['eco-regions', 'pdsi', 'tmmx', 'vs', 'soil', 'pr', 'elevation', 'agb'])\
    .classify(change_classifier)  # call this on the MBR of the AOI area instead of multiband_raster

    classified_image = classified_image.select(0)

    classified_image_asset_name = f"classified_image_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"

    if debug:
        print("Classified image created")
        print("...............................................................................")
        viz_classified(classified_image, roi, classified_image_asset_name)
    
    return classified_image, classified_image_asset_name

def test_model(test_data, roi, change_classifier, debug=False):
    """
    This function will generate predictions for the model usign the test dataset.

    """
    classified_image, classified_image_asset_name = predict_model(test_data, change_classifier, debug=debug)
    rel_bands = EXPLANATORY_VARS + ["is_burned"]
    test_samples = sample_data(test_data, roi, rel_bands, debug=debug)

    test_results = test_samples.classify(change_classifier, roi.geometry())

    print(test_results.getInfo())

    #plot_roc_curve(test_results, debug=debug)
    return classified_image, classified_image_asset_name

def viz_classified(classified_image, roi, classified_image_asset_name):
    Map = geemap.Map()
    Map.centerObject(roi, zoom=8)

    Map.addLayer(classified_image, {'min': 0, 'max': 1, 'palette': ["white", 'yellow', "orange", 'red', "brown"]}, 'Classified Image')
    Map.addLayerControl()
    Map.to_html(f'scratch/test_outputs/{classified_image_asset_name}.html')
    print(f"Predictions Asset saved as scratch/test_outputs/{classified_image_asset_name}.html")
    print("...............................................................................")

    # Pause execution to take a command line input
    user_input = input("Does the Classified Image Map Look Correct? (Y/N): ").strip().upper()

    if user_input == 'N':
        print("Exiting the program. Please check the map and try again.")
        exit()
    elif user_input != 'Y':
        raise ValueError("Invalid input. Please enter 'Y' to continue or 'N' to quit.")
    print("...............................................................................")


def test_model_ee(test_data, roi, change_classifier, folder_path, debug=False):
    classified_image_asset_name = f"classified_image_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"
    
    if not asset_exists(f"{folder_path}/{classified_image_asset_name}"):
        classified_image, classified_image_asset_name = test_model(test_data, roi, change_classifier, debug=debug)
        
        if debug:
            print(f"Exporting {classified_image_asset_name} to GEE")
            print("...............................................................................")
        task = export_to_asset(
            classified_image,
            roi.geometry(),
            folder_path=folder_path,    
            asset_name=classified_image_asset_name,
            scale=RESOLUTION
        )

        if debug:
            while task.active():
                print(f"Exporting {classified_image_asset_name}...")
                time.sleep(20)
            print("Done!")
        
    else:
        classified_image = ee.Image(f"{folder_path}/{classified_image_asset_name}")
        if debug:
            print(f"Predicted data asset {classified_image_asset_name} already exists.")
            print("...............................................................................")
    return classified_image, classified_image_asset_name
