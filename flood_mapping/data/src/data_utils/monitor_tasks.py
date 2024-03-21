import time
import ee


def monitor_tasks(tasks):
    print("Monitoring tasks...")
    completed_tasks = set()
    while len(completed_tasks) < len(tasks):
        for task in tasks:
            # Skip already completed tasks
            if task.id in completed_tasks:
                continue

            try:
                status = task.status()
                state = status.get("state")

                if state in ["COMPLETED", "FAILED", "CANCELLED"]:
                    # Handle completed tasks
                    if state == "COMPLETED":
                        print(f"Task {task.id} completed successfully.")
                    elif state == "FAILED":
                        print(
                            f"Task {task.id} failed with error: {status.get('error_message', 'No error message provided.')}"
                        )
                    elif state == "CANCELLED":
                        print(f"Task {task.id} was cancelled.")

                    completed_tasks.add(task.id)
                else:
                    # Task is still running; print its current state for monitoring
                    print(f"Task {task.id} is {state}.")
            except ee.EEException as e:
                print(f"Error checking status of task {task.id}: {e}. Will retry...")
            except Exception as general_error:
                print(f"Unexpected error: {general_error}. Will retry...")

        # Wait before the next status check to limit API requests and give time for tasks to progress
        time.sleep(
            600
        )  # Adjust the sleep time as needed based on your task's average completion time

    print("All tasks have been processed.")
