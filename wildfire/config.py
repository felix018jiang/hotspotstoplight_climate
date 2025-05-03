PROJECT_ID = "musa-wildfire-449918"
ROI_URL = "https://raw.githubusercontent.com/HotspotStoplight/CropBoxes/refs/heads/main/CR_Crop4.geojson"
ROI_NAME = 'San_Jose2'
MIN_ECOREGION_PCT = 0.1  # min area an eco-region has to overlap with the ROI to be included in the study area
RESOLUTION = 30  # in meters
SEASON_LENGTH = 3  # number of months in the calculated fire season
ANALYSIS_YEAR = 2020
SEASON_REFERENCE_START_YEAR = 2014  # range of time used to calculate fire season
SEASON_REFERENCE_END_YEAR = 2024
EXPLANATORY_VARS = ['eco-regions', 'pdsi', 'tmmx', 'vs', 'soil', 'pr', 'elevation', 'agb']  # list of band ids to train model on
DEBUG = True  # set to True to enable debug mode, which will print additional information and pause for confirmation when creating certain assets
BUCKET_NAME = "musa-wildfire-private"

# model training parameters:
NUM_POINTS = 1000  # number of points to sample for training
NUMBER_OF_TREES = 100
VARIABLES_PER_SPLIT = 3
MIN_LEAF_POPULATION = 10
BAG_FRACTION = 0.7
SEED = 42