import ee
from google.cloud import storage
import csv
from io import StringIO
import numpy as np
from collections import Counter
import ee


ee.Initialize()

def aggregate_samples(image_collection, bbox, class_values, class_points, samples_per_image, landcover_band='landcover', flooded_mask_band='flooded_mask'):
    def process_image(image):
        # Define a fixed number of samples to attempt to collect from each category per image
        samples_per_category = samples_per_image // 2  # Half for flooded, half for unflooded

        def sample_conditionally(masked_image, condition, samples_per_category):
            # Apply stratified sampling according to the known distribution
            # Assuming class_values and class_points are predefined based on analysis
            stratified_samples = masked_image.stratifiedSample(
                numPoints=samples_per_category,
                classBand=landcover_band,
                region=bbox,
                scale=30,
                seed=0,
                geometries=True,
                classValues=class_values,
                classPoints=class_points,
            )
            return stratified_samples

        # Sample for unflooded and flooded conditions
        unflooded_samples = sample_conditionally(image.updateMask(image.select(flooded_mask_band).eq(0)), 'unflooded', samples_per_category)
        flooded_samples = sample_conditionally(image.updateMask(image.select(flooded_mask_band).eq(1)), 'flooded', samples_per_category)

        return unflooded_samples.merge(flooded_samples)

    # Aggregate samples from all images
    aggregated_samples = image_collection.map(process_image).flatten()

    return aggregated_samples


def prepare_datasets(all_samples):
    print("Preparing datasets for training, testing, and validation...")

    # Split the samples into training (60%), testing (20%), and validation (20%) sets
    training_samples = all_samples.filter(ee.Filter.lt('random', 0.6))

    temp_samples = all_samples.filter(ee.Filter.gte('random', 0.6))
    testing_samples = temp_samples.filter(ee.Filter.lt('random', 0.8))

    validation_samples = temp_samples.filter(ee.Filter.gte('random', 0.8))

    class_distribution = training_samples.aggregate_histogram('flooded_mask').getInfo()
    print("Training samples class distribution:", class_distribution)

    print("Datasets prepared.")
    return training_samples, testing_samples, validation_samples


def train_classifier(training_samples, inputProperties):
    print("Training classifier...")
    classifier = ee.Classifier.smileRandomForest(10).train(
        features=training_samples,
        classProperty='flooded_mask',
        inputProperties=inputProperties
    )
    print("Classifier trained.")
    return classifier

def evaluate_classifier(testing_samples, classifier):
    print("Evaluating classifier...")
    testAccuracy = testing_samples.classify(classifier).errorMatrix('flooded_mask', 'classification')
    print("Evaluation completed.")
    return testAccuracy

def calculate_rates(confusion_matrix):
    # Convert to numpy array for easier calculations
    cm = np.array(confusion_matrix)
    
    # True Positive Rate (TPR) or Recall is calculated as TP / (TP + FN)
    # False Positive Rate (FPR) is calculated as FP / (FP + TN)
    # Where TP = True Positives, FN = False Negatives, FP = False Positives, TN = True Negatives

    TPR = []  # True Positive Rate list
    FPR = []  # False Positive Rate list

    # Calculate TPR and FPR for each class
    for i in range(len(cm)):
        TP = cm[i, i]
        FP = cm[:, i].sum() - TP
        FN = cm[i, :].sum() - TP
        TN = cm.sum() - (TP + FP + FN)
        
        TPR.append(TP / (TP + FN) if TP + FN != 0 else 0)
        FPR.append(FP / (FP + TN) if FP + TN != 0 else 0)
    
    return TPR, FPR

def export_results_to_cloud_storage(accuracyMatrix, dataset_name, bucket_name, filePrefix):
    # Ensure you have the necessary authentication to access Google Cloud Storage
    # Initialize a storage client
    storage_client = storage.Client()

    # Get the bucket
    bucket = storage_client.get_bucket(bucket_name)

    # Extract accuracy and convert the confusion matrix to a 2D array
    accuracy = accuracyMatrix.accuracy().getInfo()
    errorMatrix = accuracyMatrix.array().getInfo()

    true_positive_rates, false_positive_rates = calculate_rates(errorMatrix)

    # Prepare the CSV data using StringIO
    csv_data = StringIO()
    csv_writer = csv.writer(csv_data)
    
    # Write the accuracy on the first line
    csv_writer.writerow(['Accuracy', accuracy])
    
    csv_writer.writerow(['True Positive Rate'] + true_positive_rates)
    csv_writer.writerow(['False Positive Rate'] + false_positive_rates)
    
    # Write the header for the confusion matrix
    csv_writer.writerow(['Confusion Matrix'])
    
    # Write the rows of the confusion matrix
    csv_writer.writerows(errorMatrix)
    
    # Get the CSV content
    csv_content = csv_data.getvalue()

    # Create a blob (i.e., file) in the bucket for the combined CSV
    combined_blob = bucket.blob(f'{filePrefix}_combined.csv')

    # Upload the CSV data to the blob
    combined_blob.upload_from_string(csv_content, content_type='text/csv')

    print(f'Uploaded combined accuracy and confusion matrix to {bucket_name} with prefix {filePrefix}')

def train_and_evaluate_classifier(image_collection, bbox, bucket_name, snake_case_place_name):
    print("Starting training and evaluation process...")
    n = image_collection.size().getInfo()
    print(f"Number of images in collection: {n}")
    if n == 0:
        print("Error: Image collection is empty.")
        return
    samples_per_image = int(100000 // n)
    print(f"Samples per image: {samples_per_image}")
    inputProperties = image_collection.first().bandNames().remove('flooded_mask')
    
    landcover = ee.Image("ESA/WorldCover/v100/2020").select('Map').clip(bbox)
    
    # Sample the 'landcover' band of the image within the specified bounding box
    sample = landcover.sample(
    region=bbox,
    scale=10,  # Adjust scale as needed to match your image resolution and the granularity you need
    numPixels=25000,  # Number of pixels to sample for estimating class distribution
    seed=0,
    geometries=False  # Geometry information not required for this step
    )

    # Extract land cover class values from the sample
    # Note: The band name inside aggregate_array should match your band of interest; adjust if necessary
    sampled_values = sample.aggregate_array('Map').getInfo()

    # Calculate the histogram (frequency of each class)
    class_histogram = Counter(sampled_values)

    print(class_histogram)

    # Determine class values (unique land cover classes) and their proportional sample sizes
    class_values = list(class_histogram.keys())
    class_points = [int((freq / sum(class_histogram.values())) * samples_per_image) for freq in class_histogram.values()]
    
    all_samples = aggregate_samples(image_collection, bbox, class_values, class_points, samples_per_image)
    
    all_samples = all_samples.randomColumn()
    
    # print the distribution of flood and unflooded pixels across land cover classes
    class_distribution = all_samples.aggregate_histogram('flooded_mask').getInfo()
    print("Class distribution across land cover classes:", class_distribution)

    training_samples, testing_samples, validation_samples = prepare_datasets(all_samples)
    classifier = train_classifier(training_samples, inputProperties)
    
    testAccuracy = evaluate_classifier(testing_samples, classifier)
    validationAccuracy = evaluate_classifier(validation_samples, classifier)
    
    testFilePrefix = f'data/{snake_case_place_name}/outputs/testing_results'
    export_results_to_cloud_storage(testAccuracy, "Testing", bucket_name, testFilePrefix)
    
    valFilePrefix = f'data/{snake_case_place_name}/outputs/validation_results'
    export_results_to_cloud_storage(validationAccuracy, "Validation", bucket_name, valFilePrefix)
    
    print("Training and evaluation process completed.")
    return inputProperties, training_samples


    