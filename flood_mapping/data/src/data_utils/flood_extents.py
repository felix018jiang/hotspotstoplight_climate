import os
import json
import ee
import geemap
from geemap import geojson_to_ee



cloud_project = 'hotspotstoplight'
ee.Initialize(project = cloud_project)


# load aoi
file_path = os.path.join(os.path.dirname(__file__), '../../inputs/san_jose_aoi/resourceshedbb_CostaRica_SanJose.geojson')
absolute_path = os.path.abspath(file_path)

with open(absolute_path) as f:
    json_data = json.load(f)

aoi = geojson_to_ee(json_data) # need as a feature collection, not bounding box
bbox = aoi.geometry().bounds()

# import contextual datasets
dem = ee.Image('USGS/SRTMGL1_003').clip(bbox)
stream_dist_proximity_collection = ee.ImageCollection("projects/sat-io/open-datasets/HYDROGRAPHY90/stream-outlet-distance/stream_dist_proximity")\
    .filterBounds(bbox)\
    .mosaic()
stream_dist_proximity = stream_dist_proximity_collection.clip(bbox).rename('stream_distance')

hydro_proj = stream_dist_proximity.projection()


# get SAR data
print('Getting SAR data')

## set time frame
before_start= '2023-09-25'
before_end='2023-10-05'

after_start='2023-10-05'
after_end='2023-10-15'

# SET SAR PARAMETERS (can be left default)

# Polarization (choose either "VH" or "VV")
polarization = "VH"  # or "VV"

# Pass direction (choose either "DESCENDING" or "ASCENDING")
pass_direction = "DESCENDING"  # or "ASCENDING"

# Difference threshold to be applied on the difference image (after flood - before flood)
# It has been chosen by trial and error. Adjust as needed.
difference_threshold = 1.25

# Relative orbit (optional, if you know the relative orbit for your study area)
# relative_orbit = 79

# Load and filter Sentinel-1 GRD data by predefined parameters
collection = ee.ImageCollection('COPERNICUS/S1_GRD') \
    .filter(ee.Filter.eq('instrumentMode', 'IW')) \
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization)) \
    .filter(ee.Filter.eq('orbitProperties_pass', pass_direction)) \
    .filter(ee.Filter.eq('resolution_meters', 10)) \
    .filterBounds(aoi) \
    .select(polarization)

# Select images by predefined dates
before_collection = collection.filterDate(before_start, before_end)
after_collection = collection.filterDate(after_start, after_end)

# Create a mosaic of selected tiles and clip to the study area
before = before_collection.mosaic().clip(aoi)
after = after_collection.mosaic().clip(aoi)

# Apply radar speckle reduction by smoothing
smoothing_radius = 50
before_filtered = before.focal_mean(smoothing_radius, 'circle', 'meters')
after_filtered = after.focal_mean(smoothing_radius, 'circle', 'meters')

# Calculate the difference between the before and after images
difference = after_filtered.divide(before_filtered)

# Apply the predefined difference-threshold and create the flood extent mask
threshold = difference_threshold
difference_binary = difference.gt(threshold)

# Refine the flood result using additional datasets
swater = ee.Image('JRC/GSW1_0/GlobalSurfaceWater').select('seasonality')
swater_mask = swater.gte(10).updateMask(swater.gte(10))
flooded_mask = difference_binary.where(swater_mask, 0)
flooded = flooded_mask.updateMask(flooded_mask)
connections = flooded.connectedPixelCount()
flooded = flooded.updateMask(connections.gte(8))

# Mask out areas with more than 5 percent slope using a Digital Elevation Model
DEM = ee.Image('WWF/HydroSHEDS/03VFDEM')
terrain = ee.Algorithms.Terrain(DEM)
slope = terrain.select('slope')
flooded = flooded.updateMask(slope.lt(5))

# Set the default projection from the hydrography dataset
flooded = flooded.setDefaultProjection(hydro_proj)

# Now, reduce the resolution
print('Reducing resolution')

flooded_mode = flooded.reduceResolution(
    reducer=ee.Reducer.mode(),
    maxPixels=10000
).reproject(
    crs=hydro_proj
)

# Reproject the flooded image to match the DEM's projection
dem_projection = dem.projection()
flooded_reprojected = flooded.reproject(crs=dem_projection)

# Assuming 'flooded_mode' is your final flood detection image and 'aoi' is your area of interest

# Create a full-area mask, initially marking everything as non-flooded (value 0)
full_area_mask = ee.Image.constant(0).clip(aoi)

# Update the mask to mark flooded areas (value 1)
# Assuming flooded_mode is a binary image with 1 for flooded areas and 0 elsewhere
flood_labeled_image = full_area_mask.where(flooded_reprojected, 1)

# Now flood_labeled_image contains 1 for flooded areas and 0 for non-flooded areas

print('Exporting image')
filename = '../../outputs/test4.tif'
geemap.ee_export_image(flood_labeled_image, filename, scale=300, crs=dem_projection, region=bbox)