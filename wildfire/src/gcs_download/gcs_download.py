import ee
import geopandas as gpd
import fsspec
import json
from shapely.geometry import mapping

def ensure_full_gcs_path(bucket_name, path):
    """Ensure path includes the gs:// prefix and bucket name.

    Args:
    path: Path to the file, with or without gs:// prefix
    bucket_name: Name of the GCS bucket

    Returns:
    Full GCS path with gs:// prefix
    """
    if path and not path.startswith("gs://"):
        return f"gs://{bucket_name}/{path}"
    return path

def load_geotiff_from_gcs(bucket_name, path):
    """Safely load a GeoTIFF from GCS with proper path formatting.

    Args:
    path: Path to the GeoTIFF file (with or without gs:// prefix)
    bucket_name: GCS bucket name

    Returns:
    ee.Image object
    """
    full_path = ensure_full_gcs_path(bucket_name, path, )
    print(f"Loading GeoTIFF from: {full_path}")
    return ee.Image.loadGeoTIFF(full_path)

# def load_geojson_from_gcs(bucket_name, path):
#     """Safely load a GeoJSON from GCS with proper path formatting.

#     Args:
#     path: Path to the GeoJSON file (with or without gs:// prefix)
#     bucket_name: GCS bucket name

#     Returns:
#     ee.FeatureCollection object
#     """
#     full_path = ensure_full_gcs_path(bucket_name, path)
#     print(f"Loading GeoJSON from: {full_path}")
#     return ee.FeatureCollection(full_path)


def load_geojson_from_gcs(bucket_name, path):
    """
    Load a GeoJSON file directly from a public GCS bucket and return as an Earth Engine FeatureCollection.

    Args:
        bucket_name (str): GCS bucket name (no gs://)
        path (str): path to the GeoJSON file within the bucket

    Returns:
        ee.FeatureCollection: Earth Engine feature collection
    """
    gcs_url = f"gs://{bucket_name}/{path}"
    print(f"Reading GeoJSON from public GCS URL: {gcs_url}")

    # Read directly from GCS into GeoPandas
    with fsspec.open(gcs_url) as f:
        gdf = gpd.read_file(f)

    # Convert GeoPandas to Earth Engine FeatureCollection
    ee_features = [
    ee.Feature(ee.Geometry(mapping(geom)), row.drop("geometry").to_dict())
    for geom, (_, row) in zip(gdf.geometry, gdf.iterrows())
]
    return ee.FeatureCollection(ee_features)