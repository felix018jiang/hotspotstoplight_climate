import time
import ee
from google.cloud import storage

def export_and_monitor(geotiff, description, bucket, fileNamePrefix, scale):
    
    print(f"Starting export: {description}")
    
    # Start the export
    task = ee.batch.Export.image.toCloudStorage(
        image=geotiff,
        description=description,
        bucket=bucket,
        fileNamePrefix=fileNamePrefix,
        scale=scale,
        fileFormat='GeoTIFF'
    )
    task.start()

    # Monitor the task
    while task.active():
        print(f"Task {task.id}: {task.status()['state']}")
        time.sleep(30)  # Adjust timing as needed

    # Final status
    print(f"Task {task.id} finished with state: {task.status()['state']}")