from datetime import datetime
from data_utils.write_to_cloud import check_and_export_geotiffs_to_bucket
from data_utils.export_and_monitor import start_export_task, export_chunk
from data_utils.monitor_tasks import monitor_tasks
from data_utils.read_from_cloud import read_images_into_collection
from data_utils.train_and_eval import train_and_evaluate_classifier
from data_utils.make_data_to_classify import make_non_flooding_data
from data_utils.pygeoboundaries import get_adm_ee
from data_utils.filter_emdat import filter_data_from_gcs
from data_utils.exposure_and_vulnerability import make_vulnerability_data
from google.cloud import storage
import ee
import geemap

cloud_project = 'hotspotstoplight'

def process_flood_data(place_name):

    scale = 30
    chunk_size = 1

    if not isinstance(place_name, str):
        return "Error: Place name must be a string in quotation marks."

    snake_case_place_name = place_name.replace(' ', '_').lower()

    aoi = get_adm_ee(territories=place_name, adm='ADM0')
    bbox = aoi.geometry().bounds()

    date_pairs = filter_data_from_gcs(place_name)

    flood_dates = [(datetime.strptime(start, '%Y-%m-%d').date(), datetime.strptime(end, '%Y-%m-%d').date()) for start, end in date_pairs]

    bucket_name = f'hotspotstoplight_floodmapping'
    directory_name = f'data/{snake_case_place_name}/inputs/'

    storage_client = storage.Client(project=cloud_project)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(directory_name)
    blob.upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')
    
    check_and_export_geotiffs_to_bucket(bucket_name, directory_name, flood_dates, bbox)
    image_collection = read_images_into_collection(bucket_name, directory_name)


    ### use the image collection to train a model------------------------------------------------------------

    print("Training and assessing model...")
    
    inputProperties, training = train_and_evaluate_classifier(image_collection, bbox, bucket_name, snake_case_place_name)

    ### make final image to classify probability, write results---------------------------------------------------------------

    final_image = make_non_flooding_data(bbox)

    if training is None:
        print("Error: Training data is not available for classifier training. Exiting...")
        return

    classifier = ee.Classifier.smileRandomForest(10).setOutputMode('PROBABILITY').train(
        features=training,
        classProperty='flooded_mask',
        inputProperties=inputProperties
    )
    probabilityImage = final_image.classify(classifier)
    
    swater = ee.Image('JRC/GSW1_0/GlobalSurfaceWater').select('seasonality')
    swater_mask = swater.gte(10).updateMask(swater.gte(10))
    probabilityImage = probabilityImage.where(swater_mask, 0)

    floodProbFileNamePrefix = f'data/{snake_case_place_name}/outputs/flood_prob'

    # Create the fishnet grid
    fishnet = geemap.fishnet(bbox, h_interval=chunk_size, v_interval=chunk_size, delta=0)
    
    # Ensure fishnet is not empty by evaluating its size
    num_grids = fishnet.size().getInfo()
    if num_grids == 0:
        print("No grids were generated. Please check the bounding box and interval sizes.")
        return

    tasks = []

    print(f"Submitting {num_grids} tasks for export...")
    for index in range(num_grids):
        grid_feature = fishnet.getInfo()['features'][index]  # This might need optimization
        grid_geom = ee.Geometry.Polygon(grid_feature['geometry']['coordinates'])
        
        # Adjust the call to your export function as necessary
        print(f"Submitting task for grid {index + 1}/{num_grids}...")
        # Example function call, adjust according to your actual function's parameters
        task = export_chunk(probabilityImage, grid_geom, "Flood Probability", bucket_name, floodProbFileNamePrefix, index, num_grids, scale=scale)
        print(f"Task for grid {index + 1} submitted.")
        tasks.append(task)


    vuln = make_vulnerability_data(bbox)
    vulnFileNamePrefix = f'data/{snake_case_place_name}/outputs/vulnerability'

    task = start_export_task(vuln, "Vulnerability", bucket_name, vulnFileNamePrefix, scale=scale)
    tasks.append(task)

    monitor_tasks(tasks)

    print(f"Processing for {place_name} completed and data saved to Google Cloud in the {snake_case_place_name} directory.")