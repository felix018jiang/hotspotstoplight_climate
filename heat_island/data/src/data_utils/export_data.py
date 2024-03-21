import time
import ee
from google.cloud import storage


def start_export_task(geotiff, description, bucket, fileNamePrefix, scale):
    print(f"Initiating export: {description}")

    task = ee.batch.Export.image.toCloudStorage(
        image=geotiff,
        description=description,
        bucket=bucket,
        fileNamePrefix=fileNamePrefix,
        scale=scale,
        maxPixels=1e13,
        fileFormat="GeoTIFF",
        formatOptions={"cloudOptimized": True},
    )
    task.start()

    print(f"Export task {task.id} started for: {description}")
    return task.id  # Return the task ID for tracking
