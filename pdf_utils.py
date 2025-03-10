import io
import logging
import base64
import requests
import PyPDF2

def get_pdf_page_count(pdf_data):
    try:
        # Create a PDF reader object from the PDF data
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
        # Return the number of pages
        return len(pdf_reader.pages)
    except Exception as e:
        logging.error(f"Error reading PDF: {str(e)}")
        return 0

def is_valid_pdf_base64(pdf_base64):
    try:
        # Decode the base64 string
        pdf_data = base64.b64decode(pdf_base64)
        # Check if the first bytes match the PDF signature
        if pdf_data[:4] == b'%PDF':
            return pdf_data  # Return the valid PDF data
    except Exception as e:
        logging.error(f"Invalid base64 PDF: {str(e)}")
    return None  # Invalid PDF base64

def is_valid_pdf_url(pdf_url):
    try:
        # Fetch the PDF from the URL
        pdf_response = requests.get(pdf_url)
        if pdf_response.status_code == 200:
            content_type = pdf_response.headers.get('Content-Type', '')
            if content_type == 'application/pdf':
                return pdf_response.content  # Return the valid PDF data
        logging.error(f"Invalid PDF URL or content type: {pdf_url}")
    except Exception as e:
        logging.error(f"Error fetching PDF from URL: {str(e)}")
    return None  # Invalid PDF URL
