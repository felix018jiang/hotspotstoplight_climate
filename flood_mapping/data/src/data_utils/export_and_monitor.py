import ee


def start_export_task(geotiff, description, bucket, fileNamePrefix, scale):
    print(f"Starting export: {description}")
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
    return task


def export_chunk(
    image, grid, description, bucket_name, directory_name, index, total_grids, scale
):
    """
    Export a given chunk of an image to Cloud Storage, including printing the description
    and the grid number out of the total number of grid cells.
    """
    print(f"Starting export: {description}, Grid {index + 1} of {total_grids}")

    fileNamePrefix = f"{directory_name}/chunk_{index}"

    task = ee.batch.Export.image.toCloudStorage(
        image=image.clip(grid),
        description=f"{description} - Exporting chunk {index + 1} of {total_grids}",
        bucket=bucket_name,
        fileNamePrefix=fileNamePrefix,
        scale=scale,
        maxPixels=1e13,
    )
    task.start()
    return task
