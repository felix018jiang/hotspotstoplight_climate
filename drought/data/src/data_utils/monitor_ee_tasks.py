import ee

def monitor_specific_ee_tasks(task_ids):
    print("Checking status of specific Earth Engine tasks...")
    
    for task_id in task_ids:
        task = ee.data.getTaskStatus(task_id)[0]  # Assuming task_id is valid and [0] for first item in the returned list
        task_state = task['state']
        task_description = task['description']
        
        print(f"Task {task_id} ('{task_description}'): {task_state}")

        if task_state == 'FAILED':
            error_message = task.get('error_message', 'No error message provided.')
            print(f"Task {task_id} failed due to: {error_message}")
        elif task_state == 'COMPLETED':
            print(f"Task {task_id} completed successfully.")
        # Handle other states as needed
