import datetime
import pytz  # Required for handling time zones
import os
from flask import request, jsonify
from endesive import pdf
import pytz
import datetime
from signer import (
    load_pfx, 
    validate_args, 
    get_cn_from_cert, 
    get_issuer, 
    get_issuer_cert, 
    get_ocsp_server, 
    get_ocsp_cert_status,
    fetch_crl,
    check_if_revoked,
    check_certificate_expiry,
    validate_key_usage)
from validation import (
    validate_request_data,
    validate_pdf_data,
    validate_and_process_pdf_metadata,
    validate_and_process_pdf_page_data
)
from transaction_tracker import log_transaction
from font_size_utils import calculate_font_size
from signature_utils import prepare_signature_dict, sign_pdf
from pdf_processing import save_signed_pdf_and_send_response

used_transaction_ids = set()


def sign_pdf_pfx(request_data, txn_id, webhook_url):
    try:

        print(f"Request received from URL: {request.url}")
        print(f"Client IP: {request.remote_addr}")


         # Call validate_request_data function from validation.py
        validation_result = validate_request_data(request_data, txn_id, webhook_url)
        if 'error' in validation_result:
            return jsonify({'error': validation_result['error']}), validation_result['status']
        

         # Call validate_pdf_data function
        pdf_result = validate_pdf_data(request_data, txn_id, webhook_url)
        if 'error' in pdf_result:
            return jsonify({'error': pdf_result['error']}), pdf_result['status']

        pdf_data = pdf_result['pdf_data']


        # Call validate_and_process_pdf_metadata function
        metadata_result = validate_and_process_pdf_metadata(request_data, txn_id, webhook_url)
        if 'error' in metadata_result:
            return jsonify({'error': metadata_result['error']}), metadata_result['status']

        file_path_value = metadata_result['file_path']
        file_pin_value = metadata_result['file_pin']

        

        # Validate the PFX certificate and password
        validate_args(file_path_value, file_pin_value,txn_id, webhook_url)

  
         # Process PDF page and signature data
        page_data_result = validate_and_process_pdf_page_data(request_data, pdf_data, txn_id, webhook_url)
        if 'error' in page_data_result:
            return jsonify({'error': page_data_result['error']}), page_data_result['status']

        sigpage = page_data_result['sigpage']
        coordinates = page_data_result['coordinates']
        sigflags = page_data_result['sigflags']
        sigandcertify = page_data_result['sigandcertify']
        sigbutton = page_data_result['sigbutton']
        signaturebox = page_data_result['signaturebox']
        invisible_sign = page_data_result['invisible_sign']  # Extract this value
        # Extract processed metadata
        dateformat = metadata_result['dateformat']
        email = metadata_result['email']
        title = metadata_result['title']
        date_str = metadata_result['date_str']
        timestamp_url = metadata_result['timestamp_url']


        # Load the PFX certificate
        p12pk, p12pc, p12oc = load_pfx(file_path_value, file_pin_value, txn_id, webhook_url)

        # Get current date and time in UTC and then convert to IST
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        india_tz = pytz.timezone('Asia/Kolkata')
        signing_datetime = utc_now.astimezone(india_tz)

        validate_key_usage(p12pc, txn_id, webhook_url)

        # Fetch and check the CRL to verify if the certificate is revoked
        crl = fetch_crl(p12pc, txn_id, webhook_url)
        if crl:
            # Check if the signing certificate is revoked in CRL
            if check_if_revoked(p12pc, crl):
                log_transaction(txn_id, "failure", 'The certificate is revoked From CRL. Signing aborted. Please try another Valid certificate for signing.', webhook_url)
                raise Exception("The certificate is revoked From CRL. Signing aborted. Please try another Valid certificate for signing.")  # Stop the signing process here
            
        else:    
            cert = p12pc
            ca_issuer = get_issuer(cert, txn_id, webhook_url)
            issuer_cert = get_issuer_cert(ca_issuer, txn_id, webhook_url)
            ocsp_server = get_ocsp_server(cert, txn_id, webhook_url)
            get_ocsp_cert_status(ocsp_server, cert, issuer_cert, txn_id, webhook_url)

        check_certificate_expiry(p12pc, txn_id, webhook_url)

        

        # Extract certificate details
        cn = get_cn_from_cert(p12pc.subject.rdns)

        # Get signatory name
        signatory_name = metadata_result['signatory_name']

        # Use 'cn' if 'signatory_name' is None
        if not signatory_name:
            signatory_name = cn  # Default to 'cn' if signatory_name is None


        # Signature details
        signature_details = f"""Digitally Signed by: {signatory_name}
        Date: {metadata_result['date_str']}"""
        


        reason = request_data.get('request', {}).get('pdf', {}).get('reason')
        custom_text = request_data.get('request', {}).get('pdf', {}).get('custom_text')
        location = request_data.get('request', {}).get('pdf', {}).get('location')
        
        if reason:
            signature_details += f"\nReason: {reason}"
        if custom_text:
            signature_details += f"\nCustom Text: {custom_text}"
        if location:
            signature_details += f"\nLocation: {location}"

         # Text to calculate the font size for
        text = signature_details

        # Calculate the font size based on the provided coordinates
        font_size = calculate_font_size(text, coordinates)

        # # Print the calculated font size
        print(f"Calculated font size: {font_size}")

        # Prepare signature dictionary
        dct = prepare_signature_dict(
            txn_id=txn_id,
            sigflags=sigflags,
            sigpage=sigpage,
            sigbutton=sigbutton,
            location=location,
            signing_datetime=signing_datetime,
            reason=reason,
            invisible_sign=invisible_sign,
            font_size=font_size,
            signature_details=signature_details,
            signaturebox=signaturebox,
            sigandcertify=sigandcertify
        )



        # Sign the PDF
        if timestamp_url:
            try:
                signed_pdf_data = pdf.cms.sign(pdf_data, dct, p12pk, p12pc, p12oc, 'sha256', None, timestamp_url)
            except Exception as e:
                print(f"Error signing PDF with timestamp: {str(e)}")
                log_transaction(txn_id, "failure", f"Error signing PDF with timestamp: {str(e)}", webhook_url)
                return jsonify({'error': f"Timestamp signing failed: {str(e)}"}), 500
        else:
            signed_pdf_data = pdf.cms.sign(pdf_data, dct, p12pk, p12pc, p12oc, 'sha256', None)



        # Now use the signed_pdf_data to save the PDF and send the response
        response = save_signed_pdf_and_send_response(
            pdf_data=pdf_data,
            signed_pdf_data=signed_pdf_data,
            txn_id=txn_id,
            title=title,
            email=email,
            cn=cn,
            webhook_url=webhook_url,
            request_data=request_data
        )

        # Return the response
        return response
    

    except Exception as e:

        return jsonify({'error': str(e)}), 500