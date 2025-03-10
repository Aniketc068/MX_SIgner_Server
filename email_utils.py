import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from env import EMAILTLS, EMAILHOST, EMAILPORT, EMAILHOST_USER, EMAILHOST_PASSWORD
import threading
import queue
import time

# SMTP Configuration
EMAIL_USE_TLS = EMAILTLS
EMAIL_HOST = EMAILHOST
EMAIL_PORT = EMAILPORT
EMAIL_HOST_USER = EMAILHOST_USER
EMAIL_HOST_PASSWORD = EMAILHOST_PASSWORD

# Email Task Queue
EMAIL_QUEUE_MAXSIZE = 1000000  # Maximum tasks in queue
email_queue = queue.Queue(maxsize=EMAIL_QUEUE_MAXSIZE)

# Retry Configuration
MAX_RETRIES = 3  # Maximum retry attempts
RETRY_DELAY = 5  # Delay (in seconds) before retrying

class SMTPConnectionPool:
    """ SMTP connection pooling to reuse the same connection for multiple emails. """
    def __init__(self):
        self.server = None
        self.is_connected = False

    def get_connection(self):
        """ Get SMTP connection if not connected, else return the existing one. """
        if not self.is_connected:
            self.server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
            self.server.starttls()  # Start TLS encryption
            self.server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            self.is_connected = True
            logging.info("SMTP connection established.")
        return self.server

    def close_connection(self):
        """ Close the SMTP connection when done. """
        if self.is_connected:
            self.server.quit()
            self.is_connected = False
            logging.info("SMTP connection closed.")

# Global instance of SMTP connection pool
smtp_pool = SMTPConnectionPool()

def process_email_queue(worker_id):
    """ Function to process the email queue in a background thread. """
    while True:
        try:
            # Get email task from the queue
            task = email_queue.get()
            if task is None:
                break  # Stop the thread if a None task is received

            subject, to_email, recipient_name, attachment_path, retries = task

            # Get SMTP connection
            server = smtp_pool.get_connection()

            # Prepare the email
            msg = MIMEMultipart()
            msg['From'] = EMAIL_HOST_USER
            msg['To'] = to_email
            msg['Subject'] = subject

            # Read HTML email body
            email_html_path = 'templates/email.html'
            if os.path.exists(email_html_path):
                with open(email_html_path, 'r') as f:
                    email_body = f.read()
            else:
                raise FileNotFoundError(f"{email_html_path} not found.")

            # Replace recipient's name in the email body
            email_body = email_body.replace('[Recipient\'s Name]', recipient_name)

            msg.attach(MIMEText(email_body, 'html'))

            # Attach PDF if provided
            if attachment_path:
                part = MIMEBase('application', 'octet-stream')
                with open(attachment_path, 'rb') as file:
                    part.set_payload(file.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
                msg.attach(part)

            # Send the email
            server.sendmail(EMAIL_HOST_USER, to_email, msg.as_string())
            logging.info(f"[Worker {worker_id}] Email sent successfully to {to_email}")

        except Exception as e:
            if retries < MAX_RETRIES:
                logging.warning(f"[Worker {worker_id}] Failed to send email to {to_email}, retrying ({retries+1}/{MAX_RETRIES})...")
                time.sleep(RETRY_DELAY)
                email_queue.put((subject, to_email, recipient_name, attachment_path, retries + 1))
            else:
                logging.error(f"[Worker {worker_id}] Failed to send email to {to_email} after {MAX_RETRIES} attempts: {str(e)}")

        finally:
            # Mark the task as done
            email_queue.task_done()

def start_workers(num_workers):
    """ Start multiple worker threads. """
    for i in range(num_workers):
        worker_thread = threading.Thread(target=process_email_queue, args=(i,), daemon=True)
        worker_thread.start()

def add_email_to_queue(subject, to_email, recipient_name, attachment_path=None):
    """ Add email task to the queue. """
    try:
        email_queue.put((subject, to_email, recipient_name, attachment_path, 0), block=True)
        logging.info(f"Email task added to queue for {to_email}")
    except queue.Full:
        logging.error("Email queue is full. Unable to add more tasks.")

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Start the email processing workers
NUM_WORKERS = 1000  # Number of worker threads
start_workers(NUM_WORKERS)
