import ee

def aggregate_samples(image_collection, bbox, samples_per_image):
    def inner_aggregate(image):
        return image.stratifiedSample(
            numPoints=samples_per_image,
            classBand='flooded_mask',
            region=bbox,
            scale=30,
            seed=0
        ).randomColumn()
    return image_collection.map(inner_aggregate).flatten()

def prepare_training_testing_sets(all_samples):
    training_samples = all_samples.filter(ee.Filter.lt('random', 0.7))
    testing_samples = all_samples.filter(ee.Filter.gte('random', 0.7))
    return training_samples, testing_samples

def train_classifier(training_samples, inputProperties):
    return ee.Classifier.smileRandomForest(10).train(
        features=training_samples,
        classProperty='flooded_mask',
        inputProperties=inputProperties
    )

def classify_and_evaluate(image_collection, classifier, inputProperties, testing_samples):
    classified_images = image_collection.map(lambda image: image.select(inputProperties).classify(classifier))
    testAccuracy = testing_samples.classify(classifier).errorMatrix('flooded_mask', 'classification')
    return testAccuracy

def train_and_evaluate_classifier(image_collection, bbox):
    n = image_collection.size().getInfo()
    samples_per_image = 100000 // n
    inputProperties = image_collection.first().bandNames().remove('flooded_mask')
    
    all_samples = aggregate_samples(image_collection, bbox, samples_per_image)
    training_samples, testing_samples = prepare_training_testing_sets(all_samples)
    classifier = train_classifier(training_samples, inputProperties)    

    testAccuracy = testing_samples.classify(classifier).errorMatrix('flooded_mask', 'classification')
    accuracy = testAccuracy.accuracy().getInfo()
    confusionMatrix = testAccuracy.array().getInfo()
    
    # Calculate additional metrics
    true_positives = confusionMatrix[1][1]
    false_negatives = confusionMatrix[1][0]
    false_positives = confusionMatrix[0][1]
    true_negatives = confusionMatrix[0][0]
    recall = true_positives / (true_positives + false_negatives)
    false_positive_rate = false_positives / (false_positives + true_negatives)
    
    # Prepare and print the final assessment results
    final_assessment_result = {
        'accuracy': accuracy,
        'confusionMatrix': confusionMatrix,
        'true_positives': true_positives,
        'false_negatives': false_negatives,
        'false_positives': false_positives,
        'true_negatives': true_negatives,
        'recall': recall,
        'false_positive_rate': false_positive_rate
    }
    
    print('Confusion Matrix:', confusionMatrix)
    print('Accuracy:', accuracy)
    print('Recall:', recall)
    print('False Positive Rate:', false_positive_rate)
    
    return inputProperties, training_samples
