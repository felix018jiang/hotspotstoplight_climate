import ee
import os
import sys
import geemap
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import (
    EXPLANATORY_VARS, RESOLUTION, NUM_POINTS, 
    NUMBER_OF_TREES, VARIABLES_PER_SPLIT, 
    MIN_LEAF_POPULATION, BAG_FRACTION, SEED, ROI_NAME,
    ANALYSIS_YEAR
)

from src.validate_model.validate_model import plot_roc_curve

def make_burned_binary(multiband_raster, debug=False):
    # unmask non-burned areas and set to 0, then convert burn_date to a binary where unburned is 0, burned is 1
    binary_burned = multiband_raster.select("BurnDate").rename("is_burned").unmask(0).gt(0)  
    multiband_raster = multiband_raster.addBands(binary_burned)
    if debug:
        print("Burned binary band created")
        print("...............................................................................")
    return multiband_raster


def sample_data(multiband_raster, study_area, debug=False):
    multiband_raster = make_burned_binary(multiband_raster, debug=debug)
    #multiband_raster = multiband_raster.reproject('EPSG:4326', None, RESOLUTION)
    rel_bands = EXPLANATORY_VARS + ["is_burned"]
    explanatory_vars = multiband_raster.select(EXPLANATORY_VARS)
    if debug:
        print(f"Training Model on these variables: {explanatory_vars.bandNames().getInfo()}")
        print("...............................................................................")
    
    samples = multiband_raster.select(rel_bands).stratifiedSample(
        numPoints=NUM_POINTS,
        classBand='is_burned',
        region=study_area.geometry(),
        scale=RESOLUTION,  # Use the native resolution of your data
        seed=SEED,
        dropNulls=True,
        geometries=True
    )
    if debug:
        class_counts = samples.aggregate_histogram('is_burned')
        print(f"Sample class counts: {class_counts.getInfo()}") # prev: .getInfo()
        print("...............................................................................")
    return samples, explanatory_vars 


def train_model(multiband_raster, roi, study_area, debug=False):
    samples, explanatory_vars = sample_data(multiband_raster, study_area, debug=debug)
    change_classifier = ee.Classifier.smileRandomForest(
        numberOfTrees=NUMBER_OF_TREES,
        variablesPerSplit=VARIABLES_PER_SPLIT,
        minLeafPopulation=MIN_LEAF_POPULATION,
        bagFraction=BAG_FRACTION,
        seed=SEED
    ).setOutputMode('PROBABILITY'
    ).train(
        features=samples,
        classProperty='is_burned',
        inputProperties=explanatory_vars.bandNames()
    )

    test_results = samples.classify(change_classifier, study_area)
    #plot_roc_curve(test_results, debug=debug)

    if debug:
        print(f"Classifier trained with {NUMBER_OF_TREES} trees")
        print("...............................................................................")

    classified_image = multiband_raster.select(['eco-regions', 'pdsi', 'tmmx', 'vs', 'soil', 'pr', 'elevation', 'agb'])\
    .clip(roi.geometry())\
    .classify(change_classifier)

    classified_image = classified_image.select(0)

    classified_image_asset_name = f"classified_image_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"

    if debug:
        print("Classified image created")
        print("...............................................................................")
        viz_classified(classified_image, roi, classified_image_asset_name)
    
    return classified_image, classified_image_asset_name

def viz_classified(classified_image, roi, classified_image_asset_name):
    Map = geemap.Map()
    Map.centerObject(roi, zoom=8)

    Map.addLayer(classified_image, {'min': 0, 'max': 1, 'palette': ["white", 'yellow', "orange", 'red', "brown"]}, 'Classified Image')
    Map.addLayerControl()
    Map.to_html(f'scratch/test_outputs/{classified_image_asset_name}.html')
    print(f"Multi-Band Raster Test Map saved as scratch/test_outputs/{classified_image_asset_name}.html")
    print("...............................................................................")

    # Pause execution to take a command line input
    user_input = input("Does the Classified Image Map Look Correct? (Y/N): ").strip().upper()

    if user_input == 'N':
        print("Exiting the program. Please check the map and try again.")
        exit()
    elif user_input != 'Y':
        raise ValueError("Invalid input. Please enter 'Y' to continue or 'N' to quit.")
    print("...............................................................................")


