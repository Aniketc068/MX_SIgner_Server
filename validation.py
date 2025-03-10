# validation.py
import logging
import datetime
import base64
import requests
from date_formats import date_formats
import time
from pdf_utils import get_pdf_page_count, is_valid_pdf_base64, is_valid_pdf_url
import fitz  # PyMuPDF
from io import BytesIO
from transaction_tracker import log_transaction
import re
import platform
import os
from requests.exceptions import SSLError
from env import TSA_URL, MAX_PDF_SIZE_MB, Default_Date_Format, Default_File_Title, Default_Coordinates

used_transaction_ids = set()  # Shared resource for tracking transaction IDs


MAX_PDF_SIZE_BYTES = MAX_PDF_SIZE_MB * 1024 * 1024  # Convert to bytes


# Function to load temp email domains from a config file
def load_temp_email_domains(config_file_path):
    try:
        with open(config_file_path, 'r') as file:
            # Read all lines from the file, strip whitespace, and filter out empty lines
            temp_domains = {line.strip() for line in file.readlines() if line.strip()}
        return temp_domains
    except Exception as e:
        print(f"Error loading temp email domains: {e}")
        return set()

# Load the temp email domains from the temp-mail.config file
TEMP_EMAIL_DOMAINS = load_temp_email_domains('temp-mail.config')

# Regex pattern for validating an email address
EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zAZ0-9-]+\.[a-zA-Z0-9-.]+$'

def extract_domain(email):
    """Extracts the domain from an email address."""
    return email.split('@')[-1] if '@' in email else None

def check_https_exists(domain):
    """Check if the domain is reachable via HTTPS and has a valid SSL certificate."""
    url = f"https://{domain}"
    try:
        # Send an HTTPS request to the domain
        response = requests.get(url, timeout=10)
        
        # If the status code is 200, then the site is reachable and SSL certificate is valid
        if response.status_code == 200:
            return True
    except (requests.exceptions.RequestException, SSLError):
        return False

def is_valid_email(email):
    """Validates the email format and checks if it's a temporary email address or domain existence."""
    # If the email is empty, return 'no_email' to indicate no validation needed
    if not email:
        return 'no_email'
    
    # Check if email matches the regular expression for a valid format
    if not re.match(EMAIL_REGEX, email):
        return 'invalid_format'  # Return specific error for invalid email format
    
    # Extract the domain from the email
    domain = extract_domain(email)
    
    if not domain:
        return 'invalid_format'  # Return error if domain cannot be extracted
    
    # Check if the domain is in the list of temporary email providers
    if domain in TEMP_EMAIL_DOMAINS:
        return 'temporary_email'  # Return specific error for temporary email
    
    # Check if the domain exists using socket (SMTP port check)
    if not check_https_exists(domain):
        return 'domain_no_https'  # Return error if domain does not exist
    
    return 'valid'  # Return valid if no errors

def validate_request_data(request_data, txn_id, webhook_url):
    # Check if the command is 'managexsign'
    command = request_data.get('request', {}).get('command')
    if not command or command != "managexserversign":
        log_transaction(txn_id, "failure", "Invalid or missing command", webhook_url)
        return {'error': 'Invalid or missing command.', 'status': 400}

    # Check if the transaction ID is unique
    if txn_id in used_transaction_ids:
        log_transaction(txn_id, "failure", "Duplicate transaction ID", webhook_url)
        return {'error': 'Duplicate transaction ID', 'status': 400}
    else:
        used_transaction_ids.add(txn_id)  # Add the txn_id to the used set

    # Extract timestamp from the request data
    timestamp = request_data.get('request', {}).get('timestamp')
    if not timestamp:
        log_transaction(txn_id, "failure", "Timestamp is missing", webhook_url)
        return {'error': 'Timestamp is missing.', 'status': 400}
    
    # Validate timestamp: Must not be older than 30 seconds
    try:
        timestamp_dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        current_time = datetime.datetime.now(datetime.timezone.utc)
        time_difference = (current_time - timestamp_dt).total_seconds()
        if abs(time_difference) > 30:
            log_transaction(txn_id, "failure", "Timestamp is older than 30 seconds", webhook_url)
            return {'error': 'Timestamp is older than 30 seconds.', 'status': 400}
    except ValueError:
        log_transaction(txn_id, "failure", "Invalid timestamp format", webhook_url)
        return {'error': 'Invalid timestamp format.', 'status': 400}
    
   

    # If all checks pass
    return {'success': True}



def validate_pdf_data(request_data, txn_id, webhook_url):
    # Extract pdf_base64 and pdf_url
    pdf_base64 = request_data.get('request', {}).get('pdf_data')
    pdf_url = request_data.get('request', {}).get('pdfurl')

    if pdf_base64 and pdf_url:
        log_transaction(txn_id, "failure", "Both pdf_data and pdfurl cannot be provided together", webhook_url)
        return {'error': 'Both pdf_data and pdfurl cannot be provided together.', 'status': 400}
    
    if pdf_base64:
        pdf_data = is_valid_pdf_base64(pdf_base64)
        if not pdf_data:
            log_transaction(txn_id, "failure", "Invalid PDF in base64 format", webhook_url)
            return {'error': 'Invalid PDF in base64 format.', 'status': 400}

        # Check the size of the PDF (after base64 decoding)
        if len(pdf_data) > MAX_PDF_SIZE_BYTES:
            log_transaction(txn_id, "failure", f"PDF size exceeds {MAX_PDF_SIZE_MB}MB", webhook_url)
            return {'error': f'PDF size exceeds {MAX_PDF_SIZE_MB}MB.', 'status': 400}
    
    elif pdf_url:
        pdf_data = is_valid_pdf_url(pdf_url)
        if not pdf_data:
            log_transaction(txn_id, "failure", "Invalid or inaccessible PDF URL", webhook_url)
            return {'error': 'Invalid or inaccessible PDF URL.', 'status': 400}
        
        # Check the size of the PDF from the URL
        if len(pdf_data) > MAX_PDF_SIZE_BYTES:
            log_transaction(txn_id, "failure", f"PDF size exceeds {MAX_PDF_SIZE_MB}MB", webhook_url)
            return {'error': f'PDF size exceeds {MAX_PDF_SIZE_MB}MB.', 'status': 400}
    
    else:
        log_transaction(txn_id, "failure", "Neither valid pdf_data nor valid pdfurl was provided", webhook_url)
        return {'error': 'Neither valid pdf_data nor valid pdfurl was provided.', 'status': 400}

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

def is_valid_pdf_url(pdf_url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/pdf",
            "Accept-Encoding": "gzip, deflate, br",
        }
        response = requests.get(pdf_url, headers=headers, stream=True, timeout=10)
        
        print(f"Request to {pdf_url} - Status Code: {response.status_code}")
        
        if response.status_code == 200 and response.headers.get('Content-Type') == 'application/pdf':
            return response.content  # Valid PDF data
        else:
            print(f"Failed to retrieve PDF. Status Code: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Error accessing PDF URL: {e}")
        return None



def validate_and_process_pdf_metadata(request_data, txn_id, webhook_url):
    # Extract dateformat
    dateformat = request_data.get('request', {}).get('pdf', {}).get('dateformat', '').strip()

    # Extract email
    email = request_data.get('request', {}).get('pdf', {}).get('email', '').strip()

    # Validate email only if it's provided (not blank)
    email_validation_result = is_valid_email(email)
    
    if email_validation_result == 'invalid_format':
        log_transaction(txn_id, "failure", "Invalid email format", webhook_url)
        return {'error': 'Invalid email format.', 'status': 400}
    
    if email_validation_result == 'temporary_email':
        log_transaction(txn_id, "failure", "Temporary email address detected", webhook_url)
        return {'error': 'Temporary email address detected.', 'status': 400}
    
    if email_validation_result == 'domain_no_https':
        log_transaction(txn_id, "failure", "temporary_email", webhook_url)
        return {'error': 'Temporary email address detected.', 'status': 400}
    
    # If the email is blank, skip the validation and continue processing
    if email_validation_result == 'no_email':
        email = None  # If email is blank, set it to None or handle it as needed

    # Handle timestamp enabling logic
    enabletimestamp = request_data.get('request', {}).get('pdf', {}).get('enabletimestamp', '').lower()
    timestamp_url = None

    if enabletimestamp == "yes":
        timestamp_url = TSA_URL

    # Check if timestamp URL is set and try to contact the timestamp service
    if timestamp_url:
        try:
            response = requests.get(timestamp_url, timeout=10)  # 10 seconds timeout
            if response.status_code != 200:
                log_transaction(txn_id, "failure","Time stamping service is not working.", webhook_url)
                return {'error': 'Time stamping service is not working.', 'status': 503}
        except requests.exceptions.RequestException as e:
            log_transaction(txn_id, "failure",f"Error connecting to the time stamping service: {e}", webhook_url)
            return {'error': 'Time stamping service is not working.', 'status': 503}


    # If dateformat is not provided or invalid, default to 'dd-MMM-yyyy HH:mm:ss'
    if not dateformat or dateformat not in date_formats:
        dateformat = Default_Date_Format

    # Extract the title
    title = request_data.get('request', {}).get('pdf', {}).get('title', None)
    if not title:
        title = Default_File_Title  # Default name if title is missing or empty

    # Replace spaces in the title with underscores
    title = title.replace(" ", "_")

    # Get the current datetime and format it according to the dateformat
    signing_datetime = datetime.datetime.now()  # Correct usage of datetime.datetime
    date_str = signing_datetime.strftime(date_formats[dateformat])


    # Extract pfx_certificate and password
    SN = request_data.get('request', {}).get('pfx', {}).get('SN')

    if SN:
        SN = SN.lower()  # Convert SN to lowercase for case insensitivity

    # Validate that pfx_certificate_name and password are not blank
    if not SN:
        log_transaction(txn_id, "failure", "PFX certificate Serial No. missing", webhook_url)
        return {'error': 'PFX certificate Serial No. missing and cannot be blank.', 'status': 400}
    


    # Define file path
    if platform.system() == "Windows":
        folder_path = r"D:\project\MX_Signer_Server\save\PIN"
    else:
        folder_path = "/home/managex/Projects/MX_Signer_Server/save/PIN"

    file_path = os.path.join(folder_path, SN)  # File name should be same as SN

    # Check if file exists
    if not os.path.isfile(file_path):
        log_transaction(txn_id, "failure", f"Serial No. [{SN}] not found please upload the PFX or check the serial no. with upload pfx", webhook_url)
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
        log_transaction(txn_id, "failure", f"Error reading file {SN}: {str(e)}", webhook_url)
        return {'error': f"Error reading file {SN}: {str(e)}", 'status': 500}

    # Extract signatory name (optional)
    signatory_name = request_data.get('request', {}).get('pdf', {}).get('signatory_name', '').strip()


    # Return processed data including timestamp_url and signatory_name
    return {
        'success': True,
        'dateformat': dateformat,
        'email': email,
        'enabletimestamp': enabletimestamp,
        'timestamp_url': timestamp_url,
        'title': title,
        'date_str': date_str,
        'SN': SN,
        'file_path': file_path_value,
        'file_pin': file_pin_value,
        'signatory_name': signatory_name,
    }


def validate_and_process_pdf_page_data(request_data, pdf_data, txn_id, webhook_url):
    page_number = request_data.get('request', {}).get('pdf', {}).get('page', 1)
    total_pages = get_pdf_page_count(pdf_data)

    logging.info(f"Total Pages in PDF: {total_pages}")

    invisible_sign = request_data.get('request', {}).get('pdf', {}).get('invisiblesign', '').strip().lower()

    # Validate page number
    if page_number is None or page_number == '':
        log_transaction(txn_id, "failure", 'Please select a page number.', webhook_url)
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
                log_transaction(txn_id, "failure", 'Invalid page number format.', webhook_url)
                return {'error': 'Invalid page number format.', 'status': 400}

    # Convert to zero-based index for internal processing
    if page_number < 1 or page_number > total_pages:
        log_transaction(txn_id, "failure", 'Page Limit Exceeded.', webhook_url)
        return {'error': 'Page Limit Exceeded.', 'status': 400}
    sigpage = page_number - 1  # Convert to zero-based index

    # Get coordinates and search_by_text
    coordinates = request_data.get('request', {}).get('pdf', {}).get('coordinates', '')
    search_by_text = request_data.get('request', {}).get('pdf', {}).get('search_by_text', '').strip()

    # If both coordinates and search_by_text are provided, return an error
    if coordinates and search_by_text:
        log_transaction(txn_id, "failure", 'Please provide either coordinates or search text, not both.', webhook_url)
        return {'error': 'Please provide either coordinates or search text, not both.', 'status': 400}

    # If coordinates are blank, set default value
    if not coordinates and not search_by_text:
        coordinates = Default_Coordinates

    found_coordinates = None

    # If search_by_text is provided, find its coordinates in the PDF
    if search_by_text:
        try:
            pdf_file = BytesIO(pdf_data)
            pdf_document = fitz.open(stream=pdf_file, filetype="pdf")

            # Path to the PDF in memory
            search_text = search_by_text  # Text to search for

            # Adjusted padding values for the box
            padding_x = 10  # Horizontal padding remains the same to maintain width
            padding_y_top = 12  # Slightly reduced top padding to reduce the height
            padding_y_bottom = 50  # Slightly increased bottom padding to move the box further down

            # Specify the page number to process (1-based indexing)
            page_num = sigpage  # Page number as per human counting (1, 2, 3...)


            # Check if the page number is valid
            if 0 <= page_num < pdf_document.page_count:
                page = pdf_document.load_page(page_num)  # Load the specified page
                page_height = page.rect.height  # Get the height of the page

                # Extract all the text with its coordinates
                text_instances = page.get_text("dict")['blocks']

                # Iterate through all the blocks of text
                for block in text_instances:
                    # Check if the block contains text
                    if block['type'] == 0:  # Type 0 means text block
                        for line in block['lines']:
                            for span in line['spans']:
                                # Get the text and coordinates
                                text = span['text']
                                bbox = span.get('bbox', [])
                                if len(bbox) == 4:
                                    x1, y1, x2, y2 = bbox
                                
                                    # Check if the text matches the search text
                                    if search_text.lower() in text.lower():  # Case insensitive match
                                        print(f"Found '{search_text}' at coordinates: ({x1}, {y1}, {x2}, {y2})")
                                        
                                        # Apply padding and adjust the size of the box
                                        adjusted_y1 = int(page_height - y1) - padding_y_top  # Slightly reduce top padding
                                        adjusted_y2 = int(page_height - y2) + padding_y_bottom  # Move box further down with increased bottom padding

                                        # Apply adjusted x coordinates to width (same width with narrower padding)
                                        box_x1 = int(x1) - padding_x  # Same width, keeping horizontal padding as before
                                        box_x2 = int(x2) + padding_x  # Same width with same horizontal padding
                                        
                                        found_coordinates = (box_x1, adjusted_y1, box_x2, adjusted_y2)
                                        break

                            if found_coordinates:
                                break

                if not found_coordinates:
                    log_transaction(txn_id, "failure", f'Search text not found "{search_text}". Please use coordinates instead.', webhook_url)
                    return {'error': f'Search text not found "{search_text}". Please use coordinates instead.', 'status': 404}
                
                pdf_document.close()

        except Exception as e:
            log_transaction(txn_id, "failure",f"Error processing PDF for search text: {e}", webhook_url)
            return {'error': 'Error processing PDF for search text.', 'status': 500}




    # If coordinates are provided, ensure they are in valid format
    if coordinates:
        try:
            coordinates = [int(coord) for coord in coordinates.split(',')]
        except ValueError:
            log_transaction(txn_id, "failure", 'Invalid coordinates format.', webhook_url)
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

    # Lock PDF settings
    lockpdf = request_data.get('request', {}).get('pdf', {}).get('lockpdf', '').strip().lower()
    

    sigflags = 1 if lockpdf == "yes" else 3
    sigandcertify = lockpdf == "yes"
    sigbutton = invisible_sign != "yes"






    return {
        'success': True,
        'sigpage': sigpage,
        'coordinates': coordinates if not found_coordinates else found_coordinates,
        'sigflags': sigflags,
        'sigandcertify': sigandcertify,
        'sigbutton': sigbutton,
        'signaturebox': signaturebox,
        'invisible_sign': invisible_sign,
        'search_by_text': search_by_text  # Add this key
    }






def extract_recipient_and_cert_email(request_data, cn_name):
    # Extract recipient name from the request
    recipient_name = request_data.get('request', {}).get('pdf', {}).get('recipient', '').strip()

    # If recipient name is empty, use cn_name
    if not recipient_name:
        recipient_name = cn_name


    # Extract webhook_url from the request
    webhook_url = request_data.get('request', {}).get('parameter', {}).get('webhook_url', None)

    return {
        'recipient_name': recipient_name,
        'webhook_url': webhook_url
    }