

import ee
import requests
import requests
from requests.exceptions import RequestException
import time


def create_roi_geometry(url):
    """Create a region of interest geometry from a GeoJSON URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        geojson = requests.get(url).json()

        # Extract geometry and convert to Earth Engine geometry
        geometry = ee.Geometry(geojson["features"][0]["geometry"])

        # Wrap geometry in a FeatureCollection
        feature_collection = ee.FeatureCollection([ee.Feature(geometry)])

        return feature_collection

    except (requests.RequestException, KeyError, IndexError, ee.EEException) as e:
        print(f"Error creating ROI geometry: {e}")
        return None


def filter_ecoregions_by_area(ecoregions, roi, min_percentage=0.05):
    """Filter ecoregions by area coverage within ROI. 
    Only Retain Eco-Regions that make up at least {min_percentage} of the ROI"""

    return ecoregions.map(lambda eco_region: eco_region.set(
        'intersection_area_percentage',
        eco_region.geometry().intersection(roi.geometry()).area().divide(roi.geometry().area())
    )).filter(ee.Filter.gte('intersection_area_percentage', min_percentage))