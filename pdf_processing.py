from transaction_tracker import log_transaction
from io import BytesIO
import base64
import os
from validation import extract_recipient_and_cert_email
from email_utils import add_email_to_queue
from flask import request, jsonify

def save_signed_pdf_and_send_response(
    pdf_data, signed_pdf_data, txn_id, title, email, cn, webhook_url, request_data
):
    try:
        # Save the signed PDF to a file
        signed_pdf_filename = f"{title}_{txn_id}_signed.pdf"
        signed_pdf_path = f"signed_pdfs/{signed_pdf_filename}"

        # Ensure the directory exists
        os.makedirs('signed_pdfs', exist_ok=True)

        # Save signed PDF
        with open(signed_pdf_path, 'wb') as f:
            f.write(pdf_data)  # Original PDF data
            f.write(signed_pdf_data)  # Signed PDF data

        # Generate the URL to access the signed PDF
        signed_pdf_url = f"http://192.168.1.10:5020/signed_pdf/{signed_pdf_filename}"

        # Combine the signed PDF data into base64 for response
        output_pdf = BytesIO()
        output_pdf.write(pdf_data)  # Original PDF data
        output_pdf.write(signed_pdf_data)  # Signed PDF data
        signed_pdf_base64 = base64.b64encode(output_pdf.getvalue()).decode()

        # Extract recipient name and certemail
        recipient_data = extract_recipient_and_cert_email(request_data, cn)
        recipient_name = recipient_data['recipient_name']

        response = {
            "response": {
                "command": "managexsign",
                "ts": request_data.get('request', {}).get('timestamp'),
                "txn": txn_id,
                "status": "ok",
                "file": {
                    "attribute": {
                        "Name": cn,
                        "Type": "pdf"
                    }
                },
                "signed_pdf_url": signed_pdf_url,
                "signed_pdf_data": signed_pdf_base64
            },
        }

        if email:
            subject = f"Signed PDF Document {title}_{txn_id}_signed.pdf"
            add_email_to_queue(subject, email, recipient_name, signed_pdf_path)
            # Log email status as pending (to be updated later)
            log_transaction(txn_id, status="success", reason=f"Email Send to {email}", webhook_url=webhook_url)
            response["response"]["file"]["attribute"]["Email Status"] = "success"

        # Log the transaction status as success
        log_transaction(txn_id, status="success", reason="PDF signed successfully", webhook_url=webhook_url, response=response)

        # Return the response
        return jsonify(response)
    except Exception as e:
        # Log failure and return error
        log_transaction(txn_id, status="failure", reason=str(e), webhook_url=webhook_url)
        return jsonify({'error': str(e)}), 500
