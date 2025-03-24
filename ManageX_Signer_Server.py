import threading
from flask import Flask, request, render_template, jsonify,send_from_directory, abort
from config_loader import load_config
from sign_pdf_pfx import sign_pdf_pfx
from flask_cors import CORS
from io import BytesIO
import requests
import platform
import xml.etree.ElementTree as ET
import base64
import os
import random
import time
from werkzeug.utils import secure_filename
from transaction_tracker import log_transaction, fix_malformed_json
import shutil
import re
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa


LOG_FILE = os.path.join(os.getcwd(), 'transaction_log.json')

# Folder to save the uploaded .pfx files
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'save', 'PFX')
PIN_UPLOAD_FOLDER = os.path.join(os.getcwd(), 'save', 'PIN')  # Folder for PIN data

# Ensure the 'PFX' folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(PIN_UPLOAD_FOLDER):
    os.makedirs(PIN_UPLOAD_FOLDER)

# Initialize Flask application
app = Flask("MX_Server_Sign")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Now this will work
app.secret_key = secure_token = os.environ.get('FLASK_SECRET_KEY', ''.join(random.choices('0123456789abcdef', k=32)))

# Enable CORS support for all origins
CORS(app, resources={r"/*": {"origins": ["http://*", "https://*"]}}, supports_credentials=True)

# Allowed file extension for .pfx files
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pfx'


def serve_signed_pdf(filename):
    """Serve the signed PDF from the directory where signed PDFs are stored."""
    
    # Get the absolute path to the signed_pdf directory inside the app's directory
    signed_pdfs_dir = os.path.join(os.path.abspath(os.getcwd()), 'signed_pdfs')
    
    # Debug: Print the path to check if it's correct
    print(f"Signed PDFs directory: {signed_pdfs_dir}")
    
    # Check if the directory exists
    if not os.path.exists(signed_pdfs_dir):
        print(f"Directory not found: {signed_pdfs_dir}")
        abort(404, description="Signed PDFs directory not found")
    
    # Check if the requested file exists in the directory
    file_path = os.path.join(signed_pdfs_dir, filename)
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        abort(404, description=f"File '{filename}' not found")
    
    # Send the file from the specified directory
    return send_from_directory(signed_pdfs_dir, filename)

# Serve the signed PDF
@app.route('/signed_pdf/<filename>')
def serve_signed_pdf_route(filename):
    return serve_signed_pdf(filename)

# Custom 404 error handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Default route that shows the status of the service
@app.route('/')
def home():
    return render_template('status.html')

# Route to serve the transaction_log.json
@app.route('/transaction_log.json')
def serve_transaction_log():
    return send_from_directory(os.getcwd(), 'transaction_log.json')


# A mock list to store transaction_ids and prevent duplicates (in a real scenario, you would use a database)
existing_transaction_ids = set()

@app.route('/sign/api/v1.0/postjson', methods=['POST'])
def handle_signing_request_v1():
    try:
        # Parse the request data
        request_data = request.get_json()
        txn_id = request_data.get('request', {}).get('transaction_id')
        if not txn_id:
            return {"error": "Transaction ID is missing"}, 400

        # Call the signing function
        response = sign_pdf_pfx(request_data, txn_id)

        # Check if the response is valid
        if not response:
            log_transaction(txn_id, "failure", "Certificate Not Found")
            return {"error": "An error occurred during the signing process. Certificate Not Found."}, 500

        return response
    except Exception as e:
        log_transaction(txn_id, "failure", f"Internal server error: {str(e)}")
        return {"error": "An internal server error occurred"}, 500


@app.route('/upload', methods=['POST'])
def upload_pfx_file():
    try:
        # Print headers, form keys, and files keys for debugging
        print("Request headers:", request.headers)
        print("Request form keys:", request.form.keys())
        print("Request files keys:", request.files.keys())
        print("Raw data:", request.get_data(as_text=True))  # Debugging raw data

        # Check for the file part, making it case-insensitive
        file_key = next((key for key in request.files if key.lower() == 'file'), None)

        if not file_key:
            return jsonify({"error": "No file part"}), 400

        file = request.files[file_key]

        # Check if a file was selected
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Validate file extension
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file format. Only .pfx files are allowed"}), 400

        # Check for the PIN in the form data
        pin = next((value for key, value in request.form.items() if key.lower() == 'pin'), None)
        if not pin:
            return jsonify({"error": "PIN is required"}), 400


        # Secure the filename
        filename = secure_filename(file.filename)

        # Save the file temporarily
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Attempt to load the .pfx file with the provided PIN
        try:
            # Load the .pfx file using the PIN as password
            private_key, certificate, additional_certificates = load_pfx(file_path, pin)

            # If successful, print the Serial Number (SN) of the certificate in hex
            if certificate:
                # Convert the serial number to hexadecimal
                hex_serial_number = format(certificate.serial_number, 'x')
                print(f"Serial Number (Hex): {hex_serial_number}")

                # Save the PIN in a .txt file in PIN_UPLOAD_FOLDER with the name `f{hex_serial_number}.txt`
                pin_file_path = os.path.join(PIN_UPLOAD_FOLDER, f"{hex_serial_number}")


                # Prepare the content for the PIN .txt file
                if platform.system() == "Windows":
                    pin_content = f'file_path: "D:\\project\\MX_Signer_Server\\save\\PFX\\{file.filename}"\nfile_pin: "{pin}"'
                else:
                    pin_content = f'file_path: "/home/managex/Projects/MX_Signer_Server/save/PFX/{file.filename}"\nfile_pin: "{pin}"'
                

                # Save the PIN information to the .txt file
                with open(pin_file_path, 'w') as pin_file:
                    pin_file.write(pin_content)  # Write the content to the file
                
                # Remove the .pfx extension from the filename
                file_name_without_extension = filename.rsplit('.', 1)[0]
                
                # Return success response with original file name (without .pfx) and file path
                return jsonify({
                    "message": "File uploaded and PIN validated successfully",
                    "file_name": file_name_without_extension,  # Return file name without the .pfx extension
                    "SN": hex_serial_number  # Return the serial number in hexadecimal
                }), 200

        except ValueError as e:
            return jsonify({"error": "Invalid PIN. Could not load the PFX file."}), 400
        except Exception as e:
            return jsonify({"error": f"An error occurred while processing the PFX file: {str(e)}"}), 500

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500


def load_pfx(file_path, password):
    """Function to load pkcs12 object from the given password-protected pfx file."""
    try:
        with open(file_path, 'rb') as fp:
            pfx_data = fp.read()
            # Try to load the PFX file
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                pfx_data, password.encode(), default_backend()
            )
            # Return the certificate and any additional certs (could use this for further validation if needed)
            return private_key, certificate, additional_certificates
    except ValueError as e:
        # If ValueError is raised, it likely indicates an invalid password for the PFX file
        print(f"Error loading PFX file: Invalid password")
        raise ValueError("Invalid password for the PFX file.")
    except Exception as e:
        print(f"Error loading PFX file: {str(e)}")
        raise ValueError(f"Error loading PFX file: {str(e)}")


    
def get_folder_size(folder_path):
    total_size = 0
    # Walk through the folder and sum up the sizes of files
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            total_size += os.path.getsize(file_path)
    return total_size

def delete_files_in_folder(folder_path):
    """Deletes all files in the folder efficiently."""
    for dirpath, dirnames, filenames in os.walk(folder_path, topdown=False):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            os.remove(file_path)  # Remove the file

def monitor_folder(folder_path, max_size_mb=100, check_interval=10):
    max_size_bytes = max_size_mb * 1024 * 1024  # max size in bytes

    while True:
        folder_size = get_folder_size(folder_path)
        
        # If the folder size exceeds the limit, empty the folder
        if folder_size > max_size_bytes:
            print(f"Folder size exceeded {max_size_mb} MB. Emptying the folder...")
            delete_files_in_folder(folder_path)
            print(f"Folder has been emptied. Current size: 0 MB.")
        
        # Sleep for a longer period before checking again
        time.sleep(check_interval)  # Adjust the time interval as needed

def start_monitoring(folder_path, max_size_mb=100):
    # Running the monitoring function in a separate thread
    monitoring_thread = threading.Thread(target=monitor_folder, args=(folder_path, max_size_mb))
    monitoring_thread.daemon = True
    monitoring_thread.start()

# Folder path (change this to your actual folder path)
folder_path = 'signed_pdfs'



# Function to run the Flask app
def run_flask_app():
    config = load_config()  # Load config
    host = config.get('FLASK_HOST', '0.0.0.0')
    port = config.get('FLASK_PORT', 5020)

    app.run(host, port, use_reloader=False)  # Set use_reloader=False to prevent restart in thread

if __name__ == '__main__':

    # Fix the transaction log file
    fixed_logs = fix_malformed_json(LOG_FILE)
    
    start_monitoring(folder_path, max_size_mb=100)

    # Load config from file
    config = load_config()

    # Use the config values, fallback to defaults if not present
    host = config.get('FLASK_HOST', '0.0.0.0')
    port = config.get('FLASK_PORT', 5020)

    # Run Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()
