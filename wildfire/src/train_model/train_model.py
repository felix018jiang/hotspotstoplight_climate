import ee
import os
import sys
import geemap
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import (
    EXPLANATORY_VARS, RESOLUTION, NUM_POINTS, 
    NUMBER_OF_TREES, VARIABLES_PER_SPLIT, 
    MIN_LEAF_POPULATION, BAG_FRACTION, SEED,
    ROI_NAME, ANALYSIS_YEAR
)

from src.common import asset_exists

def sample_valid_data(multiband_raster, study_area, rel_bands, seed, max_attempts=10, debug=False):
    """
    Sample data from multiband_raster and ensure enough valid points are collected.
    
    Args:
        multiband_raster: The multiband raster to sample from
        study_area: The area to sample within
        rel_bands: Relevant bands that must not be null
        seed: Initial random seed for sampling
        max_attempts: Maximum number of resampling attempts
        debug: Whether to print debug information
    
    Returns:
        A feature collection of sample points
    """
    current_seed = seed
    attempts = 0
    
    while attempts < max_attempts:
        # Sample data with current seed
        sample_pts = sample_data(multiband_raster, study_area, rel_bands, current_seed)
        
        print(f'checking for nulls of {2* NUM_POINTS} points')
        # Filter out points with null values
        valid_pts = sample_pts.filter(ee.Filter.notNull(rel_bands))
        sample_size = valid_pts.size().getInfo()
        
        print(f"there are {sample_size} valid points")
        if debug:
            print(f"Attempt {attempts+1}: Found {sample_size} valid points out of {2 * NUM_POINTS} required")
            
        # Check if we have enough valid points
        if sample_size >= 1.25 * NUM_POINTS:
            if debug:
                class_counts = valid_pts.aggregate_histogram('is_burned')
                print(f"Sample class counts: {class_counts.getInfo()}")
                print("...............................................................................")
            return valid_pts
            
        # Try again with a new seed
        current_seed += 1
        attempts += 1
        
        if debug:
            print(f"Insufficient valid points. Resampling with seed {current_seed}")
    
    # If we get here, we've exceeded max attempts
    raise ValueError(f"Failed to collect enough valid sample points after {max_attempts} attempts")


def sample_data(multiband_raster, study_area, rel_bands, seed):
    """
    Samples training points from a multiband raster for supervised classification.

    This function performs a stratified random sampling on the 'is_burned' band
    within a given study area, ensuring balanced representation of burned and unburned classes.
    After sampling, it enriches the points with values from all relevant predictor bands
    using a point-wise reduceRegion lookup.

    Args:
        multiband_raster (ee.Image): The raster containing 'is_burned' and predictor bands.
        study_area (ee.FeatureCollection or ee.Geometry): Area to sample within.
        rel_bands (list of str): List of bands, including explanatory vars and the dependent var (is_burned).
        debug (bool): If True, print debug output. Defaults to False.

    Returns:
        ee.FeatureCollection: Sample points with 'is_burned' and predictor band values.
    """
    binary_burned = multiband_raster.select('is_burned').toInt() # make int to ensure there are only 2 classes
    
    agb_double = multiband_raster.select('agb').toDouble() # make agb a double, before it was a float- caused issues
    no_agb = [n for n in rel_bands if n != 'agb']
    multiband_raster = multiband_raster.select(no_agb).addBands(agb_double)
    
    #multiband_raster = multiband_raster.select(rel_bands)
    samples = binary_burned.stratifiedSample( # only sample the is_burned raster to ensure other bands don't interfere with class balance
        numPoints=NUM_POINTS,
        classBand='is_burned',
        region=study_area.geometry(),
        scale=RESOLUTION, 
        seed=seed,
        dropNulls=True,
        geometries=True
    )

    # add back in the other bands to the sample points:
    def map_function(feature):
        reduced = multiband_raster.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=feature.geometry(),
            scale=30
        )
        return ee.Feature(None, reduced).set('is_burned', feature.get('is_burned'))

    samples_with_all_bands = samples.map(map_function)

    print(samples_with_all_bands.limit(5).getInfo()) # need to call the samples to break up the EE computations so it doesnt time out

    return samples_with_all_bands 


def train_model(multiband_raster, study_area, debug=False):
    """
    Trains a Random Forest classifier to predict burned areas based on explanatory variables.

    Args:
        multiband_raster (ee.Image): An Earth Engine image containing explanatory bands and a binary 
            'is_burned' band indicating whether each pixel was burned.
        study_area (ee.FeatureCollection): The region from which to sample training data.
        debug (bool, optional): Whether to print debug information during training. Defaults to False.

    Returns:
        ee.Classifier: A trained Random Forest classifier with probability output mode.
    """
    rel_bands = EXPLANATORY_VARS + ["is_burned"]
    explanatory_vars = multiband_raster.select(EXPLANATORY_VARS)
    if debug:
        print(f"Training Model on these variables: {explanatory_vars.bandNames().getInfo()}")
        print("...............................................................................")
    samples = sample_valid_data(multiband_raster, study_area, rel_bands, SEED, max_attempts = 10, debug=True) # sample from the whole study area bc we train on the whole study area
    
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

    if debug:
        print(f"Classifier trained with {NUMBER_OF_TREES} trees")
        importance = change_classifier.explain().getInfo()
        print("Feature Importance:")
        print(importance['importance'])
        print("...............................................................................")
    return change_classifier


def train_model_ee(multiband_raster, study_area, folder_path, debug=False):
    classified_image_asset_name = f"classified_image_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"
    
    if not asset_exists(f"{folder_path}/{classified_image_asset_name}"):
        change_classifier = train_model(multiband_raster, study_area, debug)
        return change_classifier
        
    else:
        if debug:
            print(f"Model has already been trained and tested. Skipping model training")
            print("...............................................................................")
        return None