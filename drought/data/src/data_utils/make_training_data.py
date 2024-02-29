from datetime import datetime, timedelta
import ee
from google.cloud import storage

def make_training_data(bbox, start_date, end_date):
    
    # Convert the dates to datetime objects
    start_date = start_date
    end_date = end_date

    # Calculate the new dates
    before_start = (start_date - timedelta(days=10)).strftime("%Y-%m-%d")
    before_end = start_date.strftime("%Y-%m-%d")

    after_start = end_date.strftime("%Y-%m-%d")
    after_end = (end_date + timedelta(days=10)).strftime("%Y-%m-%d")

    print(f"Generating training data for {start_date} to {end_date}...")
    
    year_before_start = start_date - timedelta(days=365)
    start_of_year = datetime(year_before_start.year, 1, 1)
    end_of_year = datetime(year_before_start.year, 12, 31)
    
    # Load the datasets

    dem = ee.ImageCollection("projects/sat-io/open-datasets/FABDEM").mosaic().clip(bbox)
    slope = ee.Terrain.slope(dem)
    landcover = ee.Image("ESA/WorldCover/v100/2020").select('Map').clip(bbox)
    flow_direction = ee.Image('WWF/HydroSHEDS/03DIR').clip(bbox)
    ghsl = ee.Image("JRC/GHSL/P2023A/GHS_BUILT_C/2018").clip(bbox)

    stream_dist_proximity_collection = ee.ImageCollection("projects/sat-io/open-datasets/HYDROGRAPHY90/stream-outlet-distance/stream_dist_proximity")\
        .filterBounds(bbox)\
        .mosaic()
    stream_dist_proximity = stream_dist_proximity_collection.clip(bbox).rename('stream_distance')

    flow_accumulation_collection = ee.ImageCollection("projects/sat-io/open-datasets/HYDROGRAPHY90/base-network-layers/flow_accumulation")\
        .filterBounds(bbox)\
        .mosaic()
    flow_accumulation = flow_accumulation_collection.clip(bbox).rename('flow_accumulation')

    spi_collection = ee.ImageCollection("projects/sat-io/open-datasets/HYDROGRAPHY90/flow_index/spi")\
        .filterBounds(bbox)\
        .mosaic()
    spi = spi_collection.clip(bbox).rename('spi')

    sti_collection = ee.ImageCollection("projects/sat-io/open-datasets/HYDROGRAPHY90/flow_index/sti")\
        .filterBounds(bbox)\
        .mosaic()
    sti = sti_collection.clip(bbox).rename('sti')

    cti_collection = ee.ImageCollection("projects/sat-io/open-datasets/HYDROGRAPHY90/flow_index/cti")\
        .filterBounds(bbox)\
        .mosaic()
    cti = cti_collection.clip(bbox).rename('cti')

    tpi_collection = ee.ImageCollection("projects/sat-io/open-datasets/Geomorpho90m/tpi")\
        .filterBounds(bbox)\
        .mosaic()
    tpi = tpi_collection.clip(bbox).rename('tpi')

    tri_collection = ee.ImageCollection("projects/sat-io/open-datasets/Geomorpho90m/tri")\
        .filterBounds(bbox)\
        .mosaic()
    tri = tri_collection.clip(bbox).rename('tri')

    pcurv_collection = ee.ImageCollection("projects/sat-io/open-datasets/Geomorpho90m/pcurv")\
        .filterBounds(bbox)\
        .mosaic()
    pcurv = pcurv_collection.clip(bbox).rename('pcurv')

    tcurv_collection = ee.ImageCollection("projects/sat-io/open-datasets/Geomorpho90m/tcurv")\
        .filterBounds(bbox)\
        .mosaic()
    tcurv = tcurv_collection.clip(bbox).rename('tcurv')

    aspect_collection = ee.ImageCollection("projects/sat-io/open-datasets/Geomorpho90m/aspect")\
        .filterBounds(bbox)\
        .mosaic()
    aspect = aspect_collection.clip(bbox).rename('aspect')

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
        .filterBounds(bbox) \
        .select(polarization)

    # Select images by predefined dates
    before_collection = collection.filterDate(before_start, before_end)
    after_collection = collection.filterDate(after_start, after_end)

    # Check for imagery availability
    if before_collection.size().getInfo() == 0:
        print(f"No pre-event imagery available for the selected region and date range: {before_start} to {before_end}")
        return None  # Exit the function early

    if after_collection.size().getInfo() == 0:
        print(f"No post-event imagery available for the selected region and date range: {after_start} to {after_end}")
        return None  # Exit the function early

    # Create a mosaic of selected tiles and clip to the study area
    before = before_collection.mosaic().clip(bbox)
    after = after_collection.mosaic().clip(bbox)

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

    hydro_proj = stream_dist_proximity.projection()

    # Set the default projection from the hydrography dataset
    flooded = flooded.setDefaultProjection(hydro_proj)

    # Reproject the flooded image to match the DEM's projection
    dem_projection = DEM.projection()
    flooded_reprojected = flooded.reproject(crs=dem_projection)

    # Create a full-area mask, initially marking everything as non-flooded (value 0)
    full_area_mask = ee.Image.constant(0).clip(bbox)

    # Update the mask to mark flooded areas (value 1)
    # Assuming flooded_mode is a binary image with 1 for flooded areas and 0 elsewhere
    flood_labeled_image = full_area_mask.where(flooded_reprojected, 1)

    # add precipitation data
    precipitation_data = ee.ImageCollection("NASA/GDDP-CMIP6") \
        .filterBounds(bbox) \
        .filterDate(start_of_year.strftime('%Y-%m-%d'), end_of_year.strftime('%Y-%m-%d')) \
        .select('pr') \
        .filter(ee.Filter.eq('model', 'ACCESS-CM2'))

    max_precip = precipitation_data.reduce(ee.Reducer.max()) \
        .clip(bbox)

    combined = (dem.rename("elevation")
        .addBands(landcover.select('Map').rename("landcover"))
        .addBands(slope)
        .addBands(ghsl)
        .addBands(flow_direction.rename("flow_direction"))
        .addBands(stream_dist_proximity)
        .addBands(flood_labeled_image.rename("flooded_mask"))
        .addBands(flow_accumulation)
        .addBands(spi)
        .addBands(sti)
        .addBands(cti)
        .addBands(tpi)
        .addBands(tri)
        .addBands(pcurv)
        .addBands(tcurv)
        .addBands(aspect)
        .addBands(max_precip.rename("max_precip"))
        )
    
    return combined