import ee

def aggregate_samples(image_collection, bbox, samples_per_image):
    print("Starting sample aggregation...")
    def inner_aggregate(image):
        return image.stratifiedSample(
            numPoints=samples_per_image,
            classBand='flooded_mask',
            region=bbox,
            scale=30,
            seed=0
        ).randomColumn()
    aggregated_samples = image_collection.map(inner_aggregate).flatten()
    print("Number of samples aggregated: ", aggregated_samples.size().getInfo())
    print("Sample aggregation completed.")
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

def train_and_evaluate_classifier(image_collection, bbox):
    print("Starting training and evaluation process...")
    n = image_collection.size().getInfo()
    if n == 0:
        print("Error: Image collection is empty.")
        return
    samples_per_image = 100000 // n
    inputProperties = image_collection.first().bandNames().remove('flooded_mask')
    
    all_samples = aggregate_samples(image_collection, bbox, samples_per_image)
    if all_samples.size().getInfo() == 0:
        print("Error: No samples aggregated.")
        return
    
    training_samples, testing_samples, validation_samples = prepare_datasets(all_samples)
    classifier = train_classifier(training_samples, inputProperties)
    
    # Evaluate on testing set
    testAccuracy = evaluate_classifier(testing_samples, classifier)
    
    # Evaluate on validation set for an extra step of evaluation
    validationAccuracy = evaluate_classifier(validation_samples, classifier)
    
    # Prepare and print the final assessment results for both testing and validation sets
    print_results(testAccuracy, "Testing")
    print_results(validationAccuracy, "Validation")
    
    print("Training and evaluation process completed.")
    return inputProperties, training_samples

def print_results(accuracyMatrix, dataset_name):
    print(f"Processing results for {dataset_name} dataset...")
    accuracy = accuracyMatrix.accuracy().getInfo()
    confusionMatrix = accuracyMatrix.array().getInfo()
    
    # Calculate additional metrics from the confusion matrix
    true_positives = confusionMatrix[1][1]
    false_negatives = confusionMatrix[1][0]
    false_positives = confusionMatrix[0][1]
    true_negatives = confusionMatrix[0][0]
    recall = true_positives / (true_positives + false_negatives)
    false_positive_rate = false_positives / (false_positives + true_negatives)
    
    # Print the final assessment results
    print(f'{dataset_name} Confusion Matrix:', confusionMatrix)
    print(f'{dataset_name} Accuracy:', accuracy)
    print(f'{dataset_name} Recall:', recall)
    print(f'{dataset_name} False Positive Rate:', false_positive_rate)
    print(f"Results processing for {dataset_name} dataset completed.")