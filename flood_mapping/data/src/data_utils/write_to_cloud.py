from google.cloud import storage
from data_utils.make_training_data import make_training_data
from data_utils.export_and_monitor import export_and_monitor

def check_and_export_geotiffs_to_bucket(bucket_name, fileNamePrefix, flood_dates, bbox, scale=100):
    """Check for existing GeoTIFFs and export if they don't exist."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    existing_files = list(bucket.list_blobs(prefix=fileNamePrefix))
    existing_dates = [file.name.split('_')[-1].split('.')[0] for file in existing_files]  # Extract dates from file names

    for index, (start_date, end_date) in enumerate(flood_dates):
        if start_date.strftime('%Y-%m-%d') in existing_dates:
            print(f"Skipping {start_date}: data already exist")
            continue  # Skip to next iteration without exporting data for this date

        # If data for the date does not exist, proceed with export
        training_data_result = make_training_data(bbox, start_date, end_date)
        if training_data_result is None:
            print(f"Skipping export for {start_date} to {end_date}: No imagery available.")
            continue

        geotiff = training_data_result.toShort()
        specificFileNamePrefix = f'{fileNamePrefix}input_data_{start_date}'
        export_description = f'input_data_{start_date}'

        print(f"Exporting GeoTIFF {index + 1} of {len(flood_dates)}: {export_description}")
        export_and_monitor(geotiff, export_description, bucket_name, specificFileNamePrefix, scale)

        print(f"Finished checking and exporting GeoTIFFs. Processed {len(flood_dates)} flood events.")

