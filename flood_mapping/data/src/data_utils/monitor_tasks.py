import time
import ee

def monitor_tasks(tasks):
    max_attempts = 10  # Maximum attempts for exponential backoff
    initial_wait = 5  # Initial wait time in seconds

    while True:
        all_finished = True
        for task in tasks:
            attempts = 0
            wait = initial_wait
            while attempts < max_attempts:
                try:
                    status = task.status()
                    print(f"Task {task.id} status: {status['state']}")
                    break  # Exit the retry loop on successful status check
                except ee.EEException as e:
                    print(f"Error checking status of task {task.id}: {e}, retrying in {wait} seconds...")
                    time.sleep(wait)
                    wait *= 2  # Exponentially increase wait time
                    attempts += 1
                except Exception as general_error:
                    print(f"Unexpected error: {general_error}, retrying in {wait} seconds...")
                    time.sleep(wait)
                    wait *= 2
                    attempts += 1

            # After breaking out of the retry loop, process the status
            if status['state'] in ['RUNNING', 'READY']:
                all_finished = False  # At least one task is still running
            elif status['state'] == 'FAILED':
                print(f"Task {task.id} failed with error: {status.get('error_message', 'No error message provided.')}")
            elif status['state'] == 'COMPLETED':
                print(f"Task {task.id} completed successfully.")
            else:
                print(f"Task {task.id} ended with an unexpected state: {status['state']}")
            if attempts == max_attempts:
                print(f"Max attempts reached for task {task.id} without a successful status check.")

        if all_finished:
            print("All tasks completed.")
            break
        else:
            time.sleep(300)  # Sleep before checking all tasks again
