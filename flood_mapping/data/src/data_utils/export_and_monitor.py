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
        maxPixels=1e13,
        fileFormat='GeoTIFF'
    )
    task.start()

    # Monitor the task
    while task.active():
        print(f"Task {task.id}: {task.status()['state']}")
        time.sleep(120)  # Adjust timing as needed

    # Final status and explanation if failed
    final_status = task.status()
    print(f"Task {task.id} finished with state: {final_status['state']}")
    
    # Check if the task failed
    if final_status['state'] == 'FAILED':
        # Print the error message if the task failed
        error_message = final_status.get('error_message', 'No error message provided.')
        print(f"Task {task.id} failed due to: {error_message}")
    elif final_status['state'] == 'COMPLETED':
        print(f"Task {task.id} completed successfully.")
    else:
        print(f"Task {task.id} ended with an unexpected state.")
