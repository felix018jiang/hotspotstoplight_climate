import ee
from google.cloud import storage

def aggregate_samples(image_collection, bbox, samples_per_image, batch_size=10):
    images_list = image_collection.toList(image_collection.size())
    num_images = images_list.size().getInfo()
    aggregated_samples = ee.FeatureCollection([])

    # Process in batches
    for i in range(0, num_images, batch_size):
        batch_end = i + batch_size
        # Removed always printing the processing message for each batch

        batch_samples = ee.FeatureCollection([])
        batch_error = False  # Flag to track if any error occurs in the batch

        for j in range(i, min(batch_end, num_images)):
            image = ee.Image(images_list.get(j))
            try:
                result = image.stratifiedSample(
                    numPoints=samples_per_image,
                    classBand='flooded_mask',
                    region=bbox,
                    scale=30,
                    seed=0
                ).randomColumn()
                batch_samples = batch_samples.merge(result)
            except Exception as e:
                batch_error = True  # Update flag if an error occurs
                print(f"Error processing image {j + 1}: {e}")
        
        # Optionally, reduce the load on Earth Engine by limiting operations here
        aggregated_samples = aggregated_samples.merge(batch_samples)

        if batch_error:  # Print completion message only if there was an error
            print(f"Batch {i//batch_size + 1} completed with errors.")

    print("Sample aggregation completed successfully.")
    return aggregated_samples


def prepare_datasets(all_samples):
    print("Preparing datasets for training, testing, and validation...")

    # Split the samples into training (60%), testing (20%), and validation (20%) sets
    training_samples = all_samples.filter(ee.Filter.lt('random', 0.6))

    temp_samples = all_samples.filter(ee.Filter.gte('random', 0.6))
    testing_samples = temp_samples.filter(ee.Filter.lt('random', 0.8))

    validation_samples = temp_samples.filter(ee.Filter.gte('random', 0.8))

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

import ee

def export_results_to_cloud_storage(accuracy, dataset_name, bucket_name):
    # Create a feature from the scalar metric
    metrics_feature = ee.Feature(None, {
        'accuracy': accuracy
    })
    
    # Wrap this feature in a FeatureCollection
    metrics_fc = ee.FeatureCollection([metrics_feature])

    # Configure the export task for the FeatureCollection
    export_task = ee.batch.Export.table.toCloudStorage(
        collection=metrics_fc,
        description=f'export_metrics_{dataset_name}',
        bucket=bucket_name,
        fileNamePrefix=f'metrics_{dataset_name}',
        fileFormat='CSV'
    )

    # Start the export task
    export_task.start()

def train_and_evaluate_classifier(image_collection, bbox, bucket_name):
    print("Starting training and evaluation process...")
    n = image_collection.size().getInfo()
    print(f"Number of images in collection: {n}")
    if n == 0:
        print("Error: Image collection is empty.")
        return
    samples_per_image = 100000 // n
    print(f"Samples per image: {samples_per_image}")
    inputProperties = image_collection.first().bandNames().remove('flooded_mask')
    
    all_samples = aggregate_samples(image_collection, bbox, samples_per_image)
    # Instead of immediately checking if the collection is empty with .getInfo():
    # Use an Earth Engine conditional to prepare this logic
    isEmpty = ee.Algorithms.If(ee.FeatureCollection(all_samples).size().gt(0), False, True)

    # Only use .getInfo() when you absolutely need to evaluate the condition
    # if isEmpty.getInfo() == True:
        # print("No samples available for processing. Exiting...")
        # return
    
    training_samples, testing_samples, validation_samples = prepare_datasets(all_samples)
    classifier = train_classifier(training_samples, inputProperties)
    
    # Evaluate on testing set
    testAccuracy = evaluate_classifier(testing_samples, classifier)
    
    # Evaluate on validation set for an extra step of evaluation
    validationAccuracy = evaluate_classifier(validation_samples, classifier)
    
    # Prepare and print the final assessment results for both testing and validation sets
    export_results_to_cloud_storage(testAccuracy, "Testing", bucket_name)
    export_results_to_cloud_storage(validationAccuracy, "Validation", bucket_name)
    
    print("Training and evaluation process completed.")
    return inputProperties, training_samples


    