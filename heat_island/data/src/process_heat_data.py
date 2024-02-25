import ee 
import geemap
from data_utils.monitor_tasks import monitor_tasks
from data_utils.pygeoboundaries import get_adm_ee
from data_utils.export_and_monitor import start_export_task
from google.cloud import storage

cloud_project = 'hotspotstoplight'

ee.Initialize(project=cloud_project)

place_name = "Costa Rica"

startDate = '2023-01-01'
endDate = '2023-12-31'

scale = 90

snake_case_place_name = place_name.replace(' ', '_').lower()

aoi = get_adm_ee(territories=place_name, adm='ADM0')
bbox = aoi.geometry().bounds()

# Applies scaling factors.
def apply_scale_factors(image):
    # Scale and offset values for optical bands
    optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    
    # Scale and offset values for thermal bands
    thermal_bands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
    
    # Add scaled bands to the original image
    return image.addBands(optical_bands, None, True).addBands(thermal_bands, None, True)

# Function to Mask Clouds and Cloud Shadows in Landsat 8 Imagery
def cloud_mask(image):
    # Define cloud shadow and cloud bitmasks (Bits 3 and 5)
    cloud_shadow_bitmask = 1 << 3
    cloud_bitmask = 1 << 5
    
    # Select the Quality Assessment (QA) band for pixel quality information
    qa = image.select('QA_PIXEL')
    
    # Create a binary mask to identify clear conditions (both cloud and cloud shadow bits set to 0)
    mask = qa.bitwiseAnd(cloud_shadow_bitmask).eq(0).And(qa.bitwiseAnd(cloud_bitmask).eq(0))
    
    # Update the original image, masking out cloud and cloud shadow-affected pixels
    return image.updateMask(mask)

# Import and preprocess Landsat 8 imagery
image = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2") \
            .filterBounds(bbox) \
            .filterDate(startDate, endDate) \
            .map(apply_scale_factors) \
            .map(cloud_mask) \
            .median() \
            .clip(bbox)

# Calculate Normalized Difference Vegetation Index (NDVI)
ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')

# Calculate the minimum and maximum NDVI value within the bbox
# Calculate the minimum and maximum NDVI value within the bbox with adjusted maxPixels and scale
ndvi_min = ee.Number(ndvi.reduceRegion(
    reducer=ee.Reducer.min(), 
    geometry=bbox, 
    scale=scale, 
    maxPixels=1e13  # Increase maxPixels here
).values().get(0))

ndvi_max = ee.Number(ndvi.reduceRegion(
    reducer=ee.Reducer.max(), 
    geometry=bbox, 
    scale=scale, 
    maxPixels=1e13  # Increase maxPixels here
).values().get(0))

# Fraction of Vegetation (FV) Calculation
fv = ndvi.subtract(ndvi_min).divide(ndvi_max.subtract(ndvi_min)).pow(2).rename('FV')

# Emissivity Calculation
em = fv.multiply(ee.Number(0.004)).add(ee.Number(0.986)).rename('EM')

ndbi = image.normalizedDifference(['SR_B6', 'SR_B5']).rename('NDBI')
ndwi = image.normalizedDifference(['SR_B3', 'SR_B5']).rename('NDWI')

# Select Thermal Band (Band 10) and Rename It
thermal = image.select('ST_B10').rename('thermal')

# Land Surface Temperature (LST) Calculation
lst = thermal.expression(
    '(TB / (1 + (0.00115 * (TB / 1.438)) * log(em))) - 273.15', {
        'TB': thermal.select('thermal'), # Select the thermal band
        'em': em # Assign emissivity
    }).rename('LST')

landcover = ee.Image("ESA/WorldCover/v100/2020").select('Map').clip(bbox)

dem = ee.ImageCollection("projects/sat-io/open-datasets/FABDEM").mosaic().clip(bbox)

image_for_sampling = ndvi \
    .addBands(em) \
    .addBands(ndbi) \
    .addBands(ndwi) \
    .addBands(landcover.rename('landcover')) \
    .addBands(dem.rename('elevation')) \
    .addBands(ee.Image.pixelLonLat()) \
    .addBands(lst) 
    
    # Sample the combined image to create a feature collection for training
training_sample = image_for_sampling.sample(**{
    'region': bbox,
    'scale': scale,
    'numPixels': 25000,
    'seed': 0,
    'geometries': True  # Include geometries if needed for visualization
})

# Split the data into training and testing
training_sample = training_sample.randomColumn()
training = training_sample.filter(ee.Filter.lt('random', 0.7))
testing = training_sample.filter(ee.Filter.gte('random', 0.7))

# Train the Random Forest regression model
inputProperties=['NDVI', 'NDBI', 'NDWI', 'EM', 'longitude', 'latitude', 'landcover', 'elevation']
numTrees = 10  # Number of trees in the Random Forest
regressor = ee.Classifier.smileRandomForest(numTrees).setOutputMode('REGRESSION').train(
    training, 
    classProperty='LST', 
    inputProperties=inputProperties
)

# Apply the trained model to the image
predicted_image = image_for_sampling.select(inputProperties).classify(regressor)

print("Image predicted")

difference = lst.subtract(predicted_image).rename('difference')

bucket_name = f'hotspotstoplight_heatmapping'
directory_name = f'data/{snake_case_place_name}/outputs/'

storage_client = storage.Client(project=cloud_project)
bucket = storage_client.bucket(bucket_name)
blob = bucket.blob(directory_name)
blob.upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')
    
start_export_task(predicted_image, f'{place_name} LST Prediction', bucket_name, f'{directory_name}predicted', scale)