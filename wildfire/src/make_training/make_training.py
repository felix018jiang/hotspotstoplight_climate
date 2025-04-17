import ee


def read_and_clip(id, area, band, start= None, end= None):
    if start is not None and end is not None:
        band = ee.ImageCollection(id) \
            .filter(ee.Filter.date(start, end)) \
            .select(band) \
            .mean() \
            .clip(area)
    else: # for layers that don't have a date range like AGB
        band = ee.ImageCollection(id) \
            .select(band) \
            .mean() \
            .clip(area)
    return band