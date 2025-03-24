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
    validate_key_usage)
from validation import (
    validate_request_data,
    validate_pdf_data,
    validate_and_process_pdf_metadata,
    validate_and_process_pdf_page_data
)
from transaction_tracker import log_transaction
from signature_utils import prepare_signature_dict, sign_pdf
from pdf_processing import save_signed_pdf_and_send_response

used_transaction_ids = set()


def sign_pdf_pfx(request_data, txn_id):
    try:

        print(f"Request received from URL: {request.url}")
        print(f"Client IP: {request.remote_addr}")


         # Call validate_request_data function from validation.py
        validation_result = validate_request_data(request_data, txn_id)
        if 'error' in validation_result:
            return jsonify({'error': validation_result['error']}), validation_result['status']
        

         # Call validate_pdf_data function
        pdf_result = validate_pdf_data(request_data, txn_id)
        if 'error' in pdf_result:
            return jsonify({'error': pdf_result['error']}), pdf_result['status']

        pdf_data = pdf_result['pdf_data']


        # Call validate_and_process_pdf_metadata function
        metadata_result = validate_and_process_pdf_metadata(request_data, txn_id)
        if 'error' in metadata_result:
            return jsonify({'error': metadata_result['error']}), metadata_result['status']

        file_path_value = metadata_result['file_path']
        file_pin_value = metadata_result['file_pin']

        

        # Validate the PFX certificate and password
        validate_args(file_path_value, file_pin_value,txn_id)

  
         # Process PDF page and signature data
        page_data_result = validate_and_process_pdf_page_data(request_data, pdf_data, txn_id)
        if 'error' in page_data_result:
            return jsonify({'error': page_data_result['error']}), page_data_result['status']

        sigpage = page_data_result['sigpage']
        coordinates = page_data_result['coordinates']
        signaturebox = page_data_result['signaturebox']


        # Load the PFX certificate
        p12pk, p12pc, p12oc = load_pfx(file_path_value, file_pin_value, txn_id)


        validate_key_usage(p12pc, txn_id)      

        # Extract certificate details
        cn = get_cn_from_cert(p12pc.subject.rdns)



        # Signature details
        signature_details = f"""Digitally Signed by: {cn}"""



        # Prepare signature dictionary
        dct = prepare_signature_dict(
            txn_id=txn_id,
            sigpage=sigpage,
            signature_details=signature_details,
            signaturebox=signaturebox,
        )



        signed_pdf_data = pdf.cms.sign(pdf_data, dct, p12pk, p12pc, p12oc, 'sha256', None)



        # Now use the signed_pdf_data to save the PDF and send the response
        response = save_signed_pdf_and_send_response(
            pdf_data=pdf_data,
            signed_pdf_data=signed_pdf_data,
            txn_id=txn_id,
            cn=cn,
            request_data=request_data
        )

        # Return the response
        return response
    

    except Exception as e:

        return jsonify({'error': str(e)}), 500