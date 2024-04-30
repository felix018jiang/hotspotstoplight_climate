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
    bucket_name = "hotspotstoplight_floodmapping"
    file_name = "data/emdat/public_emdat_custom_request_2024-02-10_39ba89ea-de1d-4020-9b8e-027db50a5ded.xlsx"

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
    ].copy()  # Ensure this is a copy to avoid SettingWithCopyWarning

    # Process start and end dates
    for date_type in ['Start', 'End']:
        year_col = f"{date_type} Year"
        month_col = f"{date_type} Month"
        day_col = f"{date_type} Day"
        date_col = f"{date_type.lower()}_date"

        # Combine the date components into a single date column
        combined_dates = pd.to_datetime(
            {
                "year": filtered_data[year_col],
                "month": filtered_data[month_col],
                "day": filtered_data[day_col]
            }, errors='coerce')

        # Detect rows where dates could not be parsed and print them
        invalid_rows = filtered_data[combined_dates.isna()]
        if not invalid_rows.empty:
            print(f"Invalid {date_type.lower()} dates detected:")
            print(invalid_rows[[year_col, month_col, day_col]])

        # Assign parsed dates back to the main DataFrame
        filtered_data.loc[:, date_col] = combined_dates  # Use .loc to avoid warnings

    # Filter out rows where either start_date or end_date are NaT
    valid_data = filtered_data.dropna(subset=['start_date', 'end_date'])

    # Create date pairs as a list of tuples
    date_pairs = [
        (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        for start_date, end_date in zip(valid_data['start_date'], valid_data['end_date'])
    ]

    return date_pairs
