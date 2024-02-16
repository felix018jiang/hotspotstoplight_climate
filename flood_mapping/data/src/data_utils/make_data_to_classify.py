from datetime import datetime
import ee
from google.cloud import storage

def make_non_flooding_data(bbox):

    dem = ee.Image('USGS/SRTMGL1_003').clip(bbox)
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

    combined = (dem.addBands(landcover.select('Map').rename("landcover"))
        .addBands(slope)
        .addBands(ghsl)
        .addBands(flow_direction.rename("flow_direction"))
        .addBands(stream_dist_proximity)
        .addBands(flow_accumulation)
        .addBands(spi)
        .addBands(sti)
        .addBands(cti)
        .addBands(tpi)
        .addBands(tri)
        .addBands(pcurv)
        .addBands(tcurv)
        .addBands(aspect))

    return combined
