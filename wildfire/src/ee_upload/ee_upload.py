import ee
import time


def export_to_asset(ee_object, area, folder_path, asset_name, scale=None):
    """
    Export a raster or vector asset to a Google Earth Engine asset.

    Parameters:
    - ee_object: The Earth Engine object to export (either raster or vector).
    - area: vector extent of the raster or vector geometry (in the case of vector export).
    - project_id: The Google Earth Engine project ID where the asset will be stored.
    - asset_name: The name of the asset (e.g., "filtered_ecoregions_raster_30m").
    - scale: The scale/resolution of the output raster (in meters per pixel). This is used only for raster exports.

    Returns:
    - Export task object.
    """

    area = area.geometry() if hasattr(area, 'geometry') else area  # Handle vector geometry if necessary

    # Determine if the input is a raster or a vector and export accordingly
    if isinstance(ee_object, ee.Image):
        # Export raster
        export_task = ee.batch.Export.image.toAsset(
            image=ee_object,
            description=f'Export_{asset_name}',
            assetId=f'{folder_path}/{asset_name}',
            region=area,  # Define region of interest as the geometry
            scale=scale,  # Use the provided scale for raster
            maxPixels=1e13,  # Adjust depending on your raster size
        )
    elif isinstance(ee_object, ee.FeatureCollection):
        # Export vector (FeatureCollection)
        export_task = ee.batch.Export.table.toAsset(
            collection=ee_object,
            description=f'Export_{asset_name}',
            assetId=f'{folder_path}/{asset_name}',
            region=area,  # Define region of interest as the geometry
            maxFeatures=1e13,  # Adjust this based on the expected number of features
        )
    else:
        raise ValueError("The input object must be either a raster (ee.Image) or a vector (ee.FeatureCollection).")

    # Start the export task
    export_task.start()
    return export_task

def monitor_task(task, asset_name):
    print(f"Exporting {asset_name} to GEE")
    print("...............................................................................")
    while task.active():
        print(f"Exporting {asset_name}...")
        time.sleep(30)
    print("Done!")