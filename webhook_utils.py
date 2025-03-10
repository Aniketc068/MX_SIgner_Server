import requests
import json
import time
import threading
import queue
import logging

# Webhook Queue with maxsize
WEBHOOK_QUEUE_MAXSIZE = 1000000  # Maximum tasks in queue
webhook_queue = queue.Queue(maxsize=WEBHOOK_QUEUE_MAXSIZE)

# Retry Configuration
MAX_RETRIES = 3  # Maximum retry attempts
RETRY_DELAY = 5  # Delay (in seconds) before retrying

class WebhookRetryHandler:
    """Handles sending webhooks with retries."""
    def __init__(self, retries=MAX_RETRIES, delay=RETRY_DELAY):
        self.retries = retries
        self.delay = delay

    def send_webhook_with_retry(self, webhook_url, webhook_payload):
        """Sends a webhook with retry logic."""
        headers = {'Content-Type': 'application/json'}

        for attempt in range(self.retries):
            try:
                # Send the POST request
                webhook_response = requests.post(webhook_url, json=webhook_payload, headers=headers, timeout=30)

                # Check if status code is 200 or 204 for success
                if webhook_response.status_code == 200 or webhook_response.status_code == 204:
                    logging.info(f"Webhook sent successfully to {webhook_url}")
                    return True
                else:
                    logging.error(f"Failed to send webhook, status code: {webhook_response.status_code}")
                    logging.error(f"Response: {webhook_response.text}")
                    return False

            except requests.exceptions.RequestException as e:
                logging.error(f"Attempt {attempt + 1}: Failed to send webhook: {str(e)}")
                # Retry after delay
                time.sleep(self.delay)

        logging.error(f"All attempts failed to send webhook to {webhook_url}")
        return False

# Initialize webhook handler
webhook_retry_handler = WebhookRetryHandler()

def process_webhook_queue(worker_id):
    """Function to process the webhook queue in a background thread."""
    while True:
        try:
            # Get webhook task from the queue
            task = webhook_queue.get()
            if task is None:
                break  # Stop the thread if a None task is received

            webhook_url, webhook_payload = task

            # Send the webhook with retry logic
            success = webhook_retry_handler.send_webhook_with_retry(webhook_url, webhook_payload)

            if success:
                logging.info(f"[Worker {worker_id}] Successfully sent webhook to {webhook_url}")
            else:
                logging.error(f"[Worker {worker_id}] Failed to send webhook to {webhook_url}")

        except Exception as e:
            logging.error(f"[Worker {worker_id}] Error while processing webhook: {str(e)}")

        finally:
            webhook_queue.task_done()

def start_workers(num_workers):
    """Start multiple worker threads for webhook processing."""
    for i in range(num_workers):
        worker_thread = threading.Thread(target=process_webhook_queue, args=(i,), daemon=True)
        worker_thread.start()

def add_webhook_to_queue(webhook_url, webhook_payload):
    """Add webhook task to the queue."""
    try:
        webhook_queue.put((webhook_url, webhook_payload), block=True)
        logging.info(f"Webhook task added to queue for {webhook_url}")
    except queue.Full:
        logging.error("Webhook queue is full. Unable to add more tasks.")

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Start the webhook processing workers
NUM_WORKERS = 1000  # Number of worker threads
start_workers(NUM_WORKERS)

