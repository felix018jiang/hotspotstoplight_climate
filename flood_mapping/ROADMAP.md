# Project Roadmap: Flood Risk Mapping Using Google Earth Engine and Random Forest Model

## Objective
This roadmap outlines the steps to enhance the flood risk mapping project by utilizing historic flooding data from Google Earth Engine. The primary objective is to refine our model's accuracy, especially in urban contexts, and optimize our data processing pipeline.

## Roadmap

### 1. Data Validation
- **Objective:** Ensure the accuracy of the data used by comparing it with known flood risk maps.
- **Actions:**
  - Compare historical flood data with established flood risk maps.
  - Identify discrepancies and refine data collection processes to improve accuracy.

### 2. Model Evaluation and Tuning
- **Objective:** Optimize the random forest model to enhance prediction accuracy and efficiency.
- **Actions:**
  - Evaluate the current model's performance metrics.
  - Tune hyperparameters to improve model accuracy.
  - Implement cross-validation techniques to ensure the model's robustness.

### 3. Model Saving
- **Objective:** Implement a systematic approach to save trained models.
- **Actions:**
  - Develop a version control system for trained models.
  - Automate the saving process during and after training.
  - Ensure models are saved with metadata for reproducibility.

### 4. Experimentation with Training Data Sets
- **Objective:** Improve model performance in urban contexts by experimenting with various training data sets.
- **Actions:**
  - Create subsets of data focusing on urban areas.
  - Train models on these subsets to identify best practices for data representation in urban scenarios.
  - Analyze the impact of different distributions of training data on model performance.

### 5. Pipeline Improvement for Data Export
- **Objective:** Streamline the pipeline to enhance operational efficiency by managing how data is exported and handled.
- **Actions:**
  - Implement a staged data export process:
    1. Export data to be classified in tiles.
    2. Import these tiles and perform classification.
    3. Export classified tiles to a final data folder.
  - Optimize the processing steps to reduce time and computational resources.
