from data_utils.make_training_data import make_training_data
from data_utils.export_and_monitor import export_and_monitor


def export_geotiffs_to_bucket(bucket_name, fileNamePrefix, flood_dates, bbox, scale=100):
    """Export GeoTIFFs to a Google Cloud Storage bucket."""
    print(f"Number of flood events in list: {len(flood_dates)}")

    for index, (start_date, end_date) in enumerate(flood_dates):
        geotiff = make_training_data(bbox, start_date, end_date).toShort()
        specificFileNamePrefix = f'{fileNamePrefix}input_data_{start_date}'
        export_description = f'input_data_{start_date}'

        print(f"Exporting GeoTIFF {index + 1} of {len(flood_dates)}: {export_description}")
        export_and_monitor(geotiff, export_description, bucket_name, specificFileNamePrefix, scale)

    print(f"Finished exporting {len(flood_dates)} GeoTIFFs.")
