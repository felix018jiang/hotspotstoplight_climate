import ee
from data_utils.cloud_mask import cloud_mask
from data_utils.scaling_factors import apply_scale_factors


def export_ndvi_min_max(
    year, bbox, scale, gcs_bucket, snake_case_place_name, file_prefix="ndvi_min_max"
):
    try:
        startDate = ee.Date.fromYMD(year, 1, 1)
        endDate = ee.Date.fromYMD(year, 12, 31)

        # Filter the collection for the given year and bounds
        imageCollection = (
            ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
            .filterBounds(bbox)
            .filterDate(startDate, endDate)
            .map(apply_scale_factors)
            .map(cloud_mask)
        )

        # Calculate NDVI for the entire collection
        ndviCollection = imageCollection.map(
            lambda image: image.normalizedDifference(["SR_B5", "SR_B4"]).rename("NDVI")
        )

        # Reduce the collection to get min and max NDVI values
        ndvi_min = ndviCollection.reduce(ee.Reducer.min()).reduceRegion(
            reducer=ee.Reducer.min(), geometry=bbox, scale=scale, maxPixels=1e9
        )
        ndvi_max = ndviCollection.reduce(ee.Reducer.max()).reduceRegion(
            reducer=ee.Reducer.max(), geometry=bbox, scale=scale, maxPixels=1e9
        )

        # Create a feature to export
        feature = ee.Feature(
            None,
            {
                "ndvi_min": ndvi_min.get("NDVI_min"),
                "ndvi_max": ndvi_max.get("NDVI_max"),
            },
        )

        # Create and start the export task with the specified fileNamePrefix
        task = ee.batch.Export.table.toCloudStorage(
            collection=ee.FeatureCollection([feature]),
            description=f"{file_prefix}_{year}",
            bucket=gcs_bucket,
            fileNamePrefix=f"data/{snake_case_place_name}/inputs/{file_prefix}_{year}",
            fileFormat="CSV",
        )
        task.start()

        # Print statements confirming the task has started
        print(f"Starting export task for NDVI min/max values of year {year}.")

        # Return the task object
        return task

    except Exception as e:
        print(f"An error occurred while starting the export task for year {year}: {e}")
        return None
