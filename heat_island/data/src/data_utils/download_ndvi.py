def download_ndvi_data_for_year(year, cloud_project, bucket_name, snake_case_place_name):
    # Initialize the Google Cloud Storage client
    storage_client = storage.Client(project=cloud_project)
    bucket = storage_client.bucket(bucket_name)
    
    # Define the blob's name to include the full path
    blob_name = f'data/{snake_case_place_name}/inputs/ndvi_min_max_{year}.csv'
    blob = bucket.blob(blob_name)
    
    # Download the data as a string
    ndvi_data_csv = blob.download_as_string()
    
    # Parse the CSV data
    ndvi_data = csv.reader(StringIO(ndvi_data_csv.decode('utf-8')))
    rows = list(ndvi_data)
    
    # Extract NDVI min and max values
    # Assuming the first row after the header contains NDVI min and the second row contains NDVI max
    # Note: This assumes row 1 is headers
    ndvi_min = float(rows[1][1])
    ndvi_max = float(rows[1][2])
    
    return ndvi_min, ndvi_max