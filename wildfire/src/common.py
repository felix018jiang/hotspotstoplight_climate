import ee
from google.cloud import storage
from google.cloud import storage_control_v2
import re
import time
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


def export_to_asset(ee_object, area, folder_path, asset_name, scale=None):
    """
    Export a raster or vector asset to a Google Earth Engine asset.

    Parameters:
    - ee_object: The Earth Engine object to export (either raster or vector).
    - area: vector extent of the raster or vector geometry (in the case of vector export).
    - project_id: The Google Earth Engine project ID where the asset will be stored.
    - asset_name: The name of the asset (e.g., "filtered_ecoregions_raster_30m").
    - scale: The scale/resolution of the output raster (in meters per pixel). This is used only for raster exports.

    Returns:
    - Export task object.
    """

    area = area.geometry() if hasattr(area, 'geometry') else area  # Handle vector geometry if necessary

    # Determine if the input is a raster or a vector and export accordingly
    if isinstance(ee_object, ee.Image):
        # Export raster
        export_task = ee.batch.Export.image.toAsset(
            image=ee_object,
            description=f'Export_{asset_name}',
            assetId=f'{folder_path}/{asset_name}',
            region=area,  # Define region of interest as the geometry
            scale=scale,  # Use the provided scale for raster
            maxPixels=1e13,  # Adjust depending on your raster size
        )
    elif isinstance(ee_object, ee.FeatureCollection):
        # Export vector (FeatureCollection)
        export_task = ee.batch.Export.table.toAsset(
            collection=ee_object,
            description=f'Export_{asset_name}',
            assetId=f'{folder_path}/{asset_name}',
            region=area,  # Define region of interest as the geometry
            maxFeatures=1e13,  # Adjust this based on the expected number of features
        )
    else:
        raise ValueError("The input object must be either a raster (ee.Image) or a vector (ee.FeatureCollection).")

    # Start the export task
    export_task.start()
    return export_task


def asset_exists(asset_id):
    """Check the existence of the asset"""
    try:
        ee.data.getAsset(asset_id)
    except ee.EEException:
        exists = False
    else:
        exists = True
    return exists


def rasterize_ecoregions(ecoregions, scale=30):
    """Rasterize ecoregion features to a raster image."""
    raster = ecoregions.reduceToImage(
        properties=['ECO_ID'],
        reducer=ee.Reducer.first()
    ).reproject(crs='EPSG:4326', scale=scale)
    return raster


def check_and_export_geotiff_to_bucket(bucket_name, file_name, geotiff, scale):  # adapted from data_utils.write_to_cloud.py in the flood module
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Check if the file already exists in the bucket
    existing_files = list(bucket.list_blobs(prefix=file_name))
    print(f"Existing files in bucket: {[blob.name for blob in existing_files]}")
    if any(blob.name.startswith(file_name) for blob in existing_files):
        print(f"Skipping {file_name}: file already exists in bucket.")
        return

    # print(f"Initiating export for GeoTIFF: {file_name}")
    # export_description = file_name.split("/")[-1]  # Use filename as description
    # task = start_export_task(geotiff, export_description, bucket_name, file_name, scale, file_type="GeoTIFF")

    # monitor_tasks([task], sleep_interval=10)  # Monitor the task until completion
    # print("Export initiated.")


def check_and_export_geojson_to_bucket(bucket_name, file_name, geojson, scale):  # adapted from data_utils.write_to_cloud.py in the flood module
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Check if the file already exists in the bucket
    existing_files = list(bucket.list_blobs(prefix=file_name))
    print(f"Existing files in bucket: {[blob.name for blob in existing_files]}")
    if any(blob.name.startswith(file_name) for blob in existing_files):
        print(f"Skipping {file_name}: file already exists in bucket.")
        return

    # print(f"Initiating export for geojson: {file_name}")
    # export_description = file_name.split("/")[-1]  # Use filename as description
    # print(f"Export description: {export_description}")
    # task = start_export_task(geojson, export_description, bucket_name, file_name, scale, file_type="GeoJSON")

    # monitor_tasks([task], sleep_interval=10)  # Monitor the task until completion
    # print("Export initiated.")



def monitor_tasks(tasks, sleep_interval=10): # from data_utils.monitor_tasks.py in the flood module
    """
    Monitors the completion status of provided Earth Engine tasks.

    Parameters:
    - tasks: A list of Earth Engine tasks to monitor.
    - sleep_interval: Time in seconds to wait between status checks (default is 10 seconds).
    """
    print("Monitoring tasks...")
    completed_tasks = set()
    while len(completed_tasks) < len(tasks):
        for task in tasks:
            if task.id in completed_tasks:
                continue

            try:
                status = task.status()
                state = status.get("state")

                if state in ["COMPLETED", "FAILED", "CANCELLED"]:
                    if state == "COMPLETED":
                        print(f"Task {task.id} completed successfully.")
                    elif state == "FAILED":
                        print(f"Task {task.id} failed with error: {status.get('error_message', 'No error message provided.')}")
                    elif state == "CANCELLED":
                        print(f"Task {task.id} was cancelled.")
                    completed_tasks.add(task.id)
                else:
                    print(f"Task {task.id} is {state}.")
            except ee.EEException as e:
                print(f"Error checking status of task {task.id}: {e}. Will retry...")
            except Exception as general_error:
                print(f"Unexpected error: {general_error}. Will retry...")

        # Wait before the next status check to limit API requests and give time for tasks to progress
        time.sleep(sleep_interval)

    print("All tasks have been processed.")


def start_export_task(file, description, bucket, fileNamePrefix, scale, file_type):  # from data_utils.export_and_monitor.py in the flood module
    print(f"Starting export: {description}")
    if file_type == "GeoJSON":
        task = ee.batch.Export.table.toCloudStorage(
            collection=file,
            description=description,
            bucket=bucket,
            fileNamePrefix=fileNamePrefix,
            fileFormat="GeoJSON"
            )
        task.start()
    
    if file_type == "GeoTIFF":
        file = file.toFloat()
        task = ee.batch.Export.image.toCloudStorage(
            image=file,
            description=description,
            bucket=bucket,
            fileNamePrefix=fileNamePrefix,
            scale=scale,
            maxPixels=1e13,
            fileFormat="GeoTIFF",
            formatOptions={"cloudOptimized": True},
        )
        task.start()
    
    return task


def create_folder(bucket_name: str, folder_name: str) -> None:
    """Create a folder in a GCS bucket if it doesn't already exist."""
    
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
        print(f"Created folder: {response.name}")
    except AlreadyExists:
        print(f"Folder '{folder_name}' already exists. Skipping creation.")