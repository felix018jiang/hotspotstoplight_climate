from data_utils.make_training_data import make_training_data
from data_utils.export_and_monitor import start_export_task
from data_utils.monitor_tasks import monitor_tasks
import ee
from google.cloud import storage
import re


def extract_date_from_filename(filename):
    # Use a regular expression to find dates in the format YYYY-MM-DD
    match = re.search(r"\d{4}-\d{2}-\d{2}", filename)
    if match:
        return match.group(0)  # Return the first match
    else:
        return None


def check_and_export_geotiffs_to_bucket(
    bucket_name, fileNamePrefix, flood_dates, bbox, scale=90
):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    existing_files = list(bucket.list_blobs(prefix=fileNamePrefix))
    existing_dates = [
        extract_date_from_filename(file.name)
        for file in existing_files
        if extract_date_from_filename(file.name) is not None
    ]

    tasks = []

    for index, (start_date, end_date) in enumerate(flood_dates):
        if start_date.strftime("%Y-%m-%d") in existing_dates:
            print(f"Skipping {start_date}: data already exist")
            continue

        training_data_result = make_training_data(bbox, start_date, end_date)
        if training_data_result is None:
            print(
                f"Skipping export for {start_date} to {end_date}: No imagery available."
            )
            continue

        geotiff = training_data_result.toShort()
        specificFileNamePrefix = f"{fileNamePrefix}input_data_{start_date}"
        export_description = f"input_data_{start_date}"

        print(
            f"Initiating export for GeoTIFF {index + 1} of {len(flood_dates)}: {export_description}"
        )
        task = start_export_task(
            geotiff, export_description, bucket_name, specificFileNamePrefix, scale
        )
        tasks.append(task)

    if tasks:
        print("All exports initiated, monitoring task status...")
        monitor_tasks(tasks)
    else:
        print("No exports were initiated.")

    print(
        f"Finished checking and exporting GeoTIFFs. Processed {len(flood_dates)} flood events."
    )
