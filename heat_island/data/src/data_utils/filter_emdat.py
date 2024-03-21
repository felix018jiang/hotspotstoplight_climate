from google.cloud import storage
import pandas as pd
import io


def filter_data_from_gcs(country_name):
    """
    Pulls data from an Excel file in a Google Cloud Storage bucket,
    filters it based on a specified country name (case-insensitive),
    and returns the filtered data.

    Parameters:
    - country_name: The country name to filter the data by

    Returns:
    - A list of tuples with the start and end dates for the filtered rows
    """

    bucket_name = f"hotspotstoplight_floodmapping"
    file_name = f"data/emdat/public_emdat_custom_request_2024-02-10_39ba89ea-de1d-4020-9b8e-027db50a5ded.xlsx"

    # Initialize a client and get the bucket and blob
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)

    # Download the blob into an in-memory file
    content = blob.download_as_bytes()

    # Read the Excel file into a DataFrame
    excel_data = pd.read_excel(io.BytesIO(content), engine="openpyxl")

    # Filter the DataFrame based on the 'Country' column, case-insensitive
    filtered_data = excel_data[
        excel_data["Country"].str.lower() == country_name.lower()
    ]

    filtered_data = (
        filtered_data.copy()
    )  # Create a copy of the DataFrame to avoid modifying the original data
    filtered_data.loc[:, "start_date"] = pd.to_datetime(
        {
            "year": filtered_data["Start Year"],
            "month": filtered_data["Start Month"],
            "day": filtered_data["Start Day"],
        }
    )
    filtered_data.loc[:, "end_date"] = pd.to_datetime(
        {
            "year": filtered_data["End Year"],
            "month": filtered_data["End Month"],
            "day": filtered_data["End Day"],
        }
    )

    # Create date pairs as a list of tuples
    date_pairs = [
        (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        for start_date, end_date in zip(
            filtered_data["start_date"], filtered_data["end_date"]
        )
    ]

    # Return the list of date tuples
    return date_pairs
