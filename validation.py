# validation.py
import logging
import datetime
import base64
import requests
import time
from pdf_utils import get_pdf_page_count, is_valid_pdf_base64
import fitz  # PyMuPDF
from io import BytesIO
from transaction_tracker import log_transaction
import re
import platform
import os
from requests.exceptions import SSLError
from env import  MAX_PDF_SIZE_MB, Default_Coordinates

used_transaction_ids = set()  # Shared resource for tracking transaction IDs


MAX_PDF_SIZE_BYTES = MAX_PDF_SIZE_MB * 1024 * 1024  # Convert to bytes



def validate_request_data(request_data, txn_id):
    # Check if the command is 'managexsign'
    command = request_data.get('request', {}).get('command')
    if not command or command != "managexserversign":
        log_transaction(txn_id, "failure", "Invalid or missing command")
        return {'error': 'Invalid or missing command.', 'status': 400}

    # Check if the transaction ID is unique
    if txn_id in used_transaction_ids:
        log_transaction(txn_id, "failure", "Duplicate transaction ID")
        return {'error': 'Duplicate transaction ID', 'status': 400}
    else:
        used_transaction_ids.add(txn_id)  # Add the txn_id to the used set

    # Extract timestamp from the request data
    timestamp = request_data.get('request', {}).get('timestamp')
    if not timestamp:
        log_transaction(txn_id, "failure", "Timestamp is missing")
        return {'error': 'Timestamp is missing.', 'status': 400}
    
    # Validate timestamp: Must not be older than 30 seconds
    try:
        timestamp_dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        current_time = datetime.datetime.now(datetime.timezone.utc)
        time_difference = (current_time - timestamp_dt).total_seconds()
        if abs(time_difference) > 30:
            log_transaction(txn_id, "failure", "Timestamp is older than 30 seconds")
            return {'error': 'Timestamp is older than 30 seconds.', 'status': 400}
    except ValueError:
        log_transaction(txn_id, "failure", "Invalid timestamp format")
        return {'error': 'Invalid timestamp format.', 'status': 400}
    
   

    # If all checks pass
    return {'success': True}



def validate_pdf_data(request_data, txn_id):
    # Extract pdf_base64 and pdf_url
    pdf_base64 = request_data.get('request', {}).get('pdf_data')

    
    if pdf_base64:
        pdf_data = is_valid_pdf_base64(pdf_base64)
        if not pdf_data:
            log_transaction(txn_id, "failure", "Invalid PDF in base64 format")
            return {'error': 'Invalid PDF in base64 format.', 'status': 400}

        # Check the size of the PDF (after base64 decoding)
        if len(pdf_data) > MAX_PDF_SIZE_BYTES:
            log_transaction(txn_id, "failure", f"PDF size exceeds {MAX_PDF_SIZE_MB}MB")
            return {'error': f'PDF size exceeds {MAX_PDF_SIZE_MB}MB.', 'status': 400}
    
    
    else:
        log_transaction(txn_id, "failure", "Neither valid pdf_data  was provided")
        return {'error': 'Neither valid pdf_data  was provided.', 'status': 400}

    # If all checks pass, return the valid PDF data
    return {'success': True, 'pdf_data': pdf_data}

def is_valid_pdf_base64(pdf_base64):
    try:
        pdf_data = base64.b64decode(pdf_base64, validate=True)
        if pdf_data.startswith(b'%PDF'):
            return pdf_data  # Valid PDF data
    except (base64.binascii.Error, ValueError):
        return None  # Invalid base64
    return None  # Not a valid PDF


def validate_and_process_pdf_metadata(request_data, txn_id):

    # Extract pfx_certificate and password
    SN = request_data.get('request', {}).get('pfx', {}).get('SN')

    if SN:
        SN = SN.lower()  # Convert SN to lowercase for case insensitivity

    # Validate that pfx_certificate_name and password are not blank
    if not SN:
        log_transaction(txn_id, "failure", "PFX certificate Serial No. missing")
        return {'error': 'PFX certificate Serial No. missing and cannot be blank.', 'status': 400}
    


    # Define file path
    if platform.system() == "Windows":
        folder_path = r"D:\project\MX_Signer_Server\save\PIN"
    else:
        folder_path = "/home/managex/Projects/MX_Signer_Server/save/PIN"

    file_path = os.path.join(folder_path, SN)  # File name should be same as SN

    # Check if file exists
    if not os.path.isfile(file_path):
        log_transaction(txn_id, "failure", f"Serial No. [{SN}] not found please upload the PFX or check the serial no. with upload pfx")
        return {'error': f"Serial No. [{SN}] not found please upload the PFX or check the serial no. with upload pfx", 'status': 404}

    # Read and process file content
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            file_content = file.read()

            # Extract `file_path` and `file_pin` using regex
            file_path_match = re.search(r'file_path:\s*"(.+?)"', file_content)
            file_pin_match = re.search(r'file_pin:\s*"(.+?)"', file_content)

            file_path_value = file_path_match.group(1) if file_path_match else None
            file_pin_value = file_pin_match.group(1) if file_pin_match else None



    except Exception as e:
        log_transaction(txn_id, "failure", f"Error reading file {SN}: {str(e)}")
        return {'error': f"Error reading file {SN}: {str(e)}", 'status': 500}




    # Return processed data including timestamp_url and signatory_name
    return {
        'success': True,
        'SN': SN,
        'file_path': file_path_value,
        'file_pin': file_pin_value,
    }


def validate_and_process_pdf_page_data(request_data, pdf_data, txn_id):
    page_number = request_data.get('request', {}).get('pdf', {}).get('page', 1)
    total_pages = get_pdf_page_count(pdf_data)

    logging.info(f"Total Pages in PDF: {total_pages}")

    invisible_sign = request_data.get('request', {}).get('pdf', {}).get('invisiblesign', '').strip().lower()

    # Validate page number
    if page_number is None or page_number == '':
        log_transaction(txn_id, "failure", 'Please select a page number.')
        return {'error': 'Please select a page number.', 'status': 400}

    # Handle special values "first" and "last"
    if isinstance(page_number, str):
        page_number = page_number.strip().lower()
        if page_number == 'first':
            page_number = 1  # User-facing first page is 1
        elif page_number == 'last':
            page_number = total_pages  # User-facing last page is total_pages
        else:
            # Try to convert the string to an integer
            try:
                page_number = int(page_number)
            except ValueError:
                log_transaction(txn_id, "failure", 'Invalid page number format.')
                return {'error': 'Invalid page number format.', 'status': 400}

    # Convert to zero-based index for internal processing
    if page_number < 1 or page_number > total_pages:
        log_transaction(txn_id, "failure", 'Page Limit Exceeded.')
        return {'error': 'Page Limit Exceeded.', 'status': 400}
    sigpage = page_number - 1  # Convert to zero-based index

    # Get coordinates and search_by_text
    coordinates = request_data.get('request', {}).get('pdf', {}).get('coordinates', '')
    

    # If coordinates are blank, set default value
    if not coordinates:
        coordinates = Default_Coordinates

    found_coordinates = None

    

    # If coordinates are provided, ensure they are in valid format
    if coordinates:
        try:
            coordinates = [int(coord) for coord in coordinates.split(',')]
        except ValueError:
            log_transaction(txn_id, "failure", 'Invalid coordinates format.')
            return {'error': 'Invalid coordinates format.', 'status': 400}
        
    # Set signaturebox based on conditions
    if found_coordinates:
        # Use found coordinates from search
        signaturebox = None if invisible_sign == "yes" else found_coordinates
    elif coordinates:
        # Use manually provided coordinates
        signaturebox = None if invisible_sign == "yes" else coordinates
    else:
        signaturebox = None  # Default to None if no coordinates are found or provided








    return {
        'success': True,
        'sigpage': sigpage,
        'coordinates': coordinates if not found_coordinates else found_coordinates,
        'signaturebox': signaturebox,
        'invisible_sign': invisible_sign,
    }


