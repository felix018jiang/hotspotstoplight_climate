import ee

from config import ROI_NAME, ANALYSIS_YEAR, RESOLUTION
from src.ee_upload.ee_upload import export_to_asset, monitor_task
from src.common import asset_exists


def mask_water(classified_image, test_data, roi):
    
    lc = ee.ImageCollection("ESA/WorldCover/v100").select("Map").first().clip(roi)
    water = lc.select('Map').eq(80)
    Ci = classified_image.unmask()
    Ci = Ci.where(water, 0.0001)
    Ci = Ci.updateMask(Ci.gt(-1)) # to deal with the transparency issue
    
    return Ci.clip(roi) 

def mask_water_ee(classified_image, test_data, roi, folder_path, debug= False):
    water_masked_asset_name = f"classified_image_water_mask_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"
    if not asset_exists(f"{folder_path}/{water_masked_asset_name}"):
        water_masked = mask_water(classified_image, test_data, roi)
        if debug:
            print(f"{water_masked_asset_name} does not exist in GEE. Creating now.")
        
        task = export_to_asset(
            water_masked,
            test_data.geometry(),
            folder_path=folder_path,    
            asset_name=water_masked_asset_name,
            scale=RESOLUTION
        )

        if debug:
            monitor_task(task, water_masked_asset_name)
        
    else:
        water_masked = ee.Image(f"{folder_path}/{water_masked_asset_name}")
        if debug:
            print(f"Water Masked Predicted Data Asset {water_masked_asset_name} already exists.")
            print("...............................................................................")
    return water_masked