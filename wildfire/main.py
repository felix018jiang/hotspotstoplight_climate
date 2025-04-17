import ee
import geemap
import time
from src.common import initialize_EE, export_to_asset, asset_exists
from src.make_study_area.make_study_area import create_roi_geometry, filter_ecoregions_by_area
from config import PROJECT_ID, ROI_URL, ROI_NAME, MIN_ECOREGION_PCT, RESOLUTION

# Initialize Earth Engine
initialize_EE(PROJECT_ID)


# Create a folder for the output assets
folder_path = f'projects/{PROJECT_ID}/assets/{ROI_NAME}'
if not asset_exists(folder_path):
    print(f"Creating folder {folder_path} in GEE assets.")
    ee.data.createAsset({'type': 'FOLDER'}, folder_path)

# Create ROI
roi_asset_name = f"roi_{ROI_NAME}_{RESOLUTION}m"
if not asset_exists(f"{folder_path}/{roi_asset_name}"):
    roi = create_roi_geometry(ROI_URL)
    if roi is None:
        raise ValueError("Failed to create ROI geometry. Please check the URL or the response format.")
    print(f"Creating ROI asset {roi_asset_name} in GEE assets.")
    export_to_asset(ee_object=roi,
                    area=roi.geometry(),
                    folder_path=folder_path,
                    asset_name=roi_asset_name)
else:
    roi = ee.FeatureCollection(f"{folder_path}/{roi_asset_name}")


print("...............................................................................")

# Create Study Area
study_area_asset_name = f"study_area_{ROI_NAME}"

if asset_exists(study_area_asset_name):
    print("{ROI_NAME} Study Area Asset already exists.")

else:
    # Filter Ecoregions by Area
    ecoregions = ee.FeatureCollection("RESOLVE/ECOREGIONS/2017")
    study_area = filter_ecoregions_by_area(ecoregions, roi, MIN_ECOREGION_PCT)
    print(f"Filtered Ecoregions around {ROI_NAME} with minimum area percentage of {MIN_ECOREGION_PCT * 100}%")
    print("...............................................................................")

    # Test the filtered Ecoregions
    Map = geemap.Map()
    Map.centerObject(roi, zoom=6)
    Map.addLayer(study_area, {}, "Filtered Eco-Regions")
    Map.addLayer(roi, {"color": "red"}, 'ROI')
    eco_regions_filename = f"{ROI_NAME}_study_area"
    Map.to_html('scratch/test_outputs/' + eco_regions_filename + '.html')
    print(f"Study Area Test Map saved as test_outputs/{eco_regions_filename}.html")
    print("...............................................................................")
    
    # Pause execution to take a command line input
    user_input = input("Does the Study Area Map Look Correct? (Y/N): ").strip().upper()

    if user_input == 'N':
        print("Exiting the program. Please check the map and try again.")
        exit()
    elif user_input != 'Y':
        raise ValueError("Invalid input. Please enter 'Y' to continue or 'N' to quit.")
    
    # Export the filtered ecoregions to an asset
    study_area_asset_name = f"study_area_{ROI_NAME}"
    if asset_exists(study_area_asset_name):
        print(f"Eco-regions asset already exists around {ROI_NAME}.")
    else:
        task = export_to_asset(ee_object=study_area,
                                area=study_area,
                                folder_path=folder_path,
                                asset_name=study_area_asset_name)
    print(f"Export task for {study_area_asset_name} started. Check the Earth Engine Code Editor for progress.")
    print("...............................................................................")

    while task.active():
        print(f"Exporting {study_area_asset_name}...")
        time.sleep(20)

    print("Done!")