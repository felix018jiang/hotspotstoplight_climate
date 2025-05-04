import ee
from google.cloud import storage_control_v2
from google.api_core.exceptions import AlreadyExists

def initialize_EE(project_id):
    try:
        ee.Authenticate()
        ee.Initialize(project=project_id)
        print(f"Earth Engine initialized with project: {project_id}")
    except Exception as e:
        print(f"Error initializing Earth Engine: {e}")
        print("Please ensure you have authenticated and initialized Earth Engine correctly.")
        raise e
    return project_id



def asset_exists(asset_id):
    """Check the existence of the asset"""
    try:
        ee.data.getAsset(asset_id)
    except ee.EEException:
        exists = False
    else:
        exists = True
    return exists


def rasterize_ecoregions(ecoregions, scale):
    """Rasterize ecoregion features to a raster image."""
    raster = ecoregions.reduceToImage(
        properties=['ECO_ID'],
        reducer=ee.Reducer.first()
    ).reproject(crs='EPSG:4326', scale=scale) # uses nearest-neighbor resampling to get to the scale
    return raster




def create_folder(bucket_name: str, folder_name: str):
    """Create a folder in a GCS bucket if it doesn't already exist."""
    
    successful = False
    storage_control_client = storage_control_v2.StorageControlClient()

    # Construct project and bucket path
    project_path = storage_control_client.common_project_path("_")
    bucket_path = f"{project_path}/buckets/{bucket_name}"

    # Create the folder if it doesn't exist
    try:
        request = storage_control_v2.CreateFolderRequest(
            parent=bucket_path,
            folder_id=folder_name,
        )
        response = storage_control_client.create_folder(request=request)
        successful = True
    except AlreadyExists:
        successful = False
    return successful