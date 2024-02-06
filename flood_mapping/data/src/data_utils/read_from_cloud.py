from google.cloud import storage
import ee

def list_gcs_files(bucket_name, prefix):
    """List all files in a GCS bucket folder."""
    storage_client = storage.Client()
    blobs = storage_client.list_blobs(bucket_name, prefix=prefix)
    return [f"gs://{bucket_name}/{blob.name}" for blob in blobs if blob.name.endswith('.tif')]

def read_images_into_collection(bucket_name, prefix):
    """Read images from cloud bucket into an Earth Engine image collection."""
    tif_list = list_gcs_files(bucket_name, prefix)
    print(tif_list)

    print("Reading images from cloud bucket into image collection...")
    ee_image_list = [ee.Image.loadGeoTIFF(url) for url in tif_list]
    image_collection = ee.ImageCollection.fromImages(ee_image_list)

    info = image_collection.size().getInfo()
    print(f'Collection contains {info} images.')
    
    return image_collection
