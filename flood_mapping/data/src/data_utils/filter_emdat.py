from google.cloud import storage
import pandas as pd
import io

def filter_data_from_gcs(bucket_name, file_name, country_name):
    """
    Pulls data from an Excel file in a Google Cloud Storage bucket,
    filters it based on a specified country name (case-insensitive),
    and returns the filtered data.

    Parameters:
    - bucket_name: Name of the Google Cloud Storage bucket
    - file_name: Name of the file within the bucket
    - country_name: The country name to filter the data by

    Returns:
    - A DataFrame with the filtered rows
    """

    # Initialize a client and get the bucket and blob
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)

    # Download the blob into an in-memory file
    content = blob.download_as_bytes()

    # Read the Excel file into a DataFrame
    excel_data = pd.read_excel(io.BytesIO(content), engine='openpyxl')

    # Filter the DataFrame based on the 'Country' column, case-insensitive
    filtered_data = excel_data[excel_data['Country'].str.lower() == country_name.lower()]

    return filtered_data

# Example usage
bucket_name = 'your_bucket_name'
file_name = 'your_file_name.xlsx'
country_name = 'Your Country Name'

filtered_data = filter_data_from_gcs(bucket_name, file_name, country_name)
print(filtered_data)
