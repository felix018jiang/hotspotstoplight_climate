import ee
from data_utils.cloud_mask import cloud_mask
from data_utils.scaling_factors import apply_scale_factors


def process_year(year, bbox, ndvi_min, ndvi_max):
    # Define the start and end dates for the year
    startDate = ee.Date.fromYMD(year, 1, 1)
    endDate = ee.Date.fromYMD(year, 12, 31)

    # Import and preprocess Landsat 8 imagery for the year
    imageCollection = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2") \
                .filterBounds(bbox) \
                .filterDate(startDate, endDate) \
                .map(apply_scale_factors) \
                .map(cloud_mask)

    # Function to calculate LST for each image in the collection
    def calculate_lst(image):
        # Calculate Normalized Difference Vegetation Index (NDVI)
        ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
        
        # Use the passed ndvi_min and ndvi_max directly instead of calculating them
        # Convert them to ee.Number since they are likely passed as Python primitives
        ndvi_min_ee = ee.Number(ndvi_min)
        ndvi_max_ee = ee.Number(ndvi_max)

        # Fraction of Vegetation (FV) Calculation
        fv = ee.Image().expression(
            "(ndvi - ndvi_min) / (ndvi_max - ndvi_min)",
            {
                'ndvi': ndvi,
                'ndvi_max': ndvi_max_ee,
                'ndvi_min': ndvi_min_ee
            }
        ).pow(2).rename('FV')

        # Emissivity Calculation
        em = fv.multiply(ee.Number(0.004)).add(ee.Number(0.986)).rename('EM')

        # Select Thermal Band (Band 10) and Rename It
        thermal = image.select('ST_B10').rename('thermal')

        # Land Surface Temperature (LST) Calculation
        lst = thermal.expression(
            '(TB / (1 + (0.00115 * (TB / 1.438)) * log(em))) - 273.15', {
                'TB': thermal.select('thermal'), # Select the thermal band
                'em': em # Assign emissivity
            }).rename('LST')

        return lst

    # Apply the calculate_lst function to each image in the collection
    lstCollection = imageCollection.map(calculate_lst)

    # Create a binary image for each image in the collection where 1 indicates LST >= 33 and 0 otherwise
    hotDaysCollection = lstCollection.map(lambda image: image.gte(33))

    # Sum all the binary images in the collection to get the total number of hot days in the year
    hotDaysYear = hotDaysCollection.sum()

    landcover = ee.Image("ESA/WorldCover/v100/2020").select('Map').clip(bbox)

    dem = ee.ImageCollection("projects/sat-io/open-datasets/FABDEM").mosaic().clip(bbox)

    image_for_sampling = landcover.rename('landcover') \
        .addBands(dem.rename('elevation')) \
        .addBands(ee.Image.pixelLonLat()) \
        .addBands(hotDaysYear.rename('hot_days')
                  ) 
        
    # print("Sampling image band names", image_for_sampling.bandNames().getInfo())

    return image_for_sampling