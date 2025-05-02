import ee
import os
import sys
import geemap
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import (
    EXPLANATORY_VARS, RESOLUTION, NUM_POINTS, 
    NUMBER_OF_TREES, VARIABLES_PER_SPLIT, 
    MIN_LEAF_POPULATION, BAG_FRACTION, SEED
)

from src.common import asset_exists
from src.ee_upload.ee_upload import export_to_asset


def sample_data(multiband_raster, study_area, rel_bands, debug=False):
    samples = multiband_raster.select(rel_bands).stratifiedSample(
        numPoints=NUM_POINTS,
        classBand='is_burned',
        region=study_area.geometry(),
        scale=RESOLUTION, 
        seed=SEED,
        dropNulls=True,
        geometries=True
    )
    if debug:
        class_counts = samples.aggregate_histogram('is_burned')
        print(f"Sample class counts: {class_counts.getInfo()}") 
        print("...............................................................................")
    return samples 


def train_model(multiband_raster, study_area, debug=False):
    rel_bands = EXPLANATORY_VARS + ["is_burned"]
    explanatory_vars = multiband_raster.select(EXPLANATORY_VARS)
    if debug:
        print(f"Training Model on these variables: {explanatory_vars.bandNames().getInfo()}")
        print("...............................................................................")
    samples = sample_data(multiband_raster, study_area, rel_bands, debug=debug)

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
        print("...............................................................................")
    return change_classifier

    