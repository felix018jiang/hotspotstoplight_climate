from google.cloud import storage
import time
import ee


def file_exists_in_bucket(bucket_name, file_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    existing_files = list(bucket.list_blobs(prefix=file_name))
    if any(blob.name.startswith(file_name) for blob in existing_files):
        return True
    else:
        return False


def check_and_export_geotiff_to_bucket(bucket_name, file_name, geotiff, scale):  # adapted from data_utils.write_to_cloud.py in the flood module
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Check if the file already exists in the bucket
    existing_files = list(bucket.list_blobs(prefix=file_name))
    if any(blob.name.startswith(file_name) for blob in existing_files):
        print(f"Skipping {file_name}: file already exists in bucket.")
        return

    print(f"Initiating export for GeoTIFF: {file_name}")
    export_description = file_name.split("/")[-1]  # Use filename as description
    task = start_export_task(geotiff, export_description, bucket_name, file_name, scale, file_type="GeoTIFF")

    monitor_tasks([task], sleep_interval=10)  # Monitor the task until completion
    print("Export initiated.")


def check_and_export_geojson_to_bucket(bucket_name, file_name, geojson, scale):  # adapted from data_utils.write_to_cloud.py in the flood module
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Check if the file already exists in the bucket
    existing_files = list(bucket.list_blobs(prefix=file_name))
    print(f"Existing files in bucket: {[blob.name for blob in existing_files]}")
    if any(blob.name.startswith(file_name) for blob in existing_files):
        print(f"Skipping {file_name}: file already exists in bucket.")
        return

    print(f"Initiating export for geojson: {file_name}")
    export_description = file_name.split("/")[-1]  # Use filename as description
    print(f"Export description: {export_description}")
    task = start_export_task(geojson, export_description, bucket_name, file_name, scale, file_type="GeoJSON")

    monitor_tasks([task], sleep_interval=10)  # Monitor the task until completion
    print("Export initiated.")



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


def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"
    # The path to your file to upload
    # source_file_name = "local/path/to/file"
    # The ID of your GCS object
    # destination_blob_name = "storage-object-name"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    generation_match_precondition = 0

    blob.upload_from_filename(source_file_name, if_generation_match=generation_match_precondition)

    print(
        f"File {source_file_name} uploaded to {destination_blob_name}."
    )