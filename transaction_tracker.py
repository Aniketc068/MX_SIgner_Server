import os
import json
import re
import threading
import queue


# Path to the transaction log file
LOG_FILE = os.path.join(os.getcwd(), 'transaction_log.json')

# Ensure the log file exists
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w') as f:
        json.dump([], f)

# Queue to hold logs that need to be written to the file
log_queue = queue.Queue()

# Lock to ensure thread-safety when writing to the log file
file_lock = threading.Lock()

def write_to_log_file():
    """
    Worker thread that listens to the log queue and writes entries to the log file one at a time.
    """
    while True:
        try:
            # Wait for a log entry from the queue
            log_entry = log_queue.get()

            # Get the current logs
            with open(LOG_FILE, 'r') as f:
                logs = json.load(f)

            # Append the new log entry
            logs.append(log_entry)

            # Write the updated logs back to the file with file locking
            with file_lock:
                with open(LOG_FILE, 'w') as f:
                    json.dump(logs, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())


            # Mark the task as done
            log_queue.task_done()

        except Exception as e:
            print(f"Error in log file writing thread: {e}")

def start_logging_thread():
    """
    Starts the worker thread to process log entries from the queue.
    """
    thread = threading.Thread(target=write_to_log_file, daemon=True)
    thread.start()

def log_transaction(transaction_id, status, reason=None, response=None, **kwargs):
    """
    Log a transaction with its status and reason (if any), and optionally send it to a webhook.

    Args:
        transaction_id (str): The transaction ID.
        status (str): The status of the transaction ('success' or 'failure').
        reason (str, optional): The reason for failure, if applicable.
    """
    try:
        # Prepare the log entry
        log_entry = {
            "transaction_id": transaction_id,
            "status": status,
            "reason": reason
        }

        # Add the log entry to the queue
        log_queue.put(log_entry)

    except Exception as e:
        print(f"Error logging transaction: {e}")

def get_transactions():
    """
    Retrieve all logged transactions.
    
    Returns:
        list: A list of transaction logs.
    """
    try:
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading transaction logs: {e}")
        return []

def fix_malformed_json(file_path):
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            return []

        # Read the raw content of the file
        with open(file_path, 'r') as f:
            content = f.read()

        # Attempt to fix the content
        content = re.sub(r'\]\s*{', '}, {', content)
        content = content.strip().rstrip(',')
        if not content.startswith('['):
            content = '[' + content
        if not content.endswith(']'):
            content += ']'

        # Validate JSON
        logs = json.loads(content)

        # Save the corrected JSON back
        with open(file_path, 'w') as f:
            json.dump(logs, f, indent=4)
            f.flush()
            os.fsync(f.fileno())

        return logs

    except json.JSONDecodeError as jde:
        return []

    except Exception as e:
        return []

# Start the logging thread when the program begins
start_logging_thread()
