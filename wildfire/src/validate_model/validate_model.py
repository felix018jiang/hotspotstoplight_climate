import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import roc_curve, auc
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import (
    ROI_NAME, ANALYSIS_YEAR, RESOLUTION, BUCKET_NAME
)

from src.gcs_upload.gcs_upload import upload_blob

# Function to get ROC curve data from Earth Engine
def get_roc_data(test_results, property_name='classification'):
    """
    Extract actual and predicted values from Earth Engine FeatureCollection
    to calculate ROC curve
    """
    
    # Get the actual and predicted values
    features = test_results.getInfo()['features']
    
    y_true = []
    y_pred = []
    
    for feature in features:
        props = feature['properties']
        y_true.append(props['is_burned'])
        y_pred.append(props[property_name])
    print(f"y_true: {y_true}")
    print(f"y_pred: {y_pred}")  
    
    return np.array(y_true), np.array(y_pred)

def plot_roc_curve(test_results, debug):
    roc_asset_name = f"roc_curve_{ROI_NAME}_{ANALYSIS_YEAR}_{RESOLUTION}m"
# Get ROC data from test results
    y_true, y_scores = get_roc_data(test_results)

    # Calculate ROC curve
    fpr, tpr, thresholds = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)

    # Plot ROC curve
    plt.figure(figsize=(10, 8))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.3f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic (ROC) Curve for Wildfire Prediction')
    plt.legend(loc="lower right")
    plt.grid(True, alpha=0.3)

    plt.savefig(f'scratch/test_outputs/{roc_asset_name}.png', dpi=300, bbox_inches='tight')
    upload_blob(
        BUCKET_NAME,
        f'scratch/test_outputs/{roc_asset_name}.png',
        f'performance_metrics/{roc_asset_name}.png'
    )


    if debug:
        print(f"ROC curve saved as {roc_asset_name}.png")
        print("...............................................................................")
        # Pause execution to take a command line input
        user_input = input("Does the ROC Curve Look Correct? (Y/N): ").strip().upper()

        if user_input == 'N':
            print("Exiting the program. Please check the map and try again.")
            exit()
        elif user_input != 'Y':
            raise ValueError("Invalid input. Please enter 'Y' to continue or 'N' to quit.")
        print("...............................................................................")
