# signature_utils.py

from endesive import pdf

def prepare_signature_dict(txn_id, sigflags, sigpage, sigbutton, location, signing_datetime, reason, invisible_sign, font_size, signature_details, signaturebox, sigandcertify):
    """Prepare the signature dictionary for signing."""
    dct = {
        "sigflags": sigflags,
        "sigfield": f"MX Signer Server {txn_id}",
        "sigpage": sigpage,
        "sigbutton": sigbutton,
        "contact": "N/A",
        "location": location if location else 'N/A',
        "signingdate": signing_datetime.strftime('%Y%m%d%H%M%S+05\'30\'').encode(),
        "reason": reason if reason else 'N/A',
        "text": {
                'wraptext': True,
                'fontsize': font_size,
                'textalign': 'left',
                'linespacing': 1,
            } if not invisible_sign == "yes" else None,  # Remove text block if invisible
        "signature": signature_details,
        "signaturebox": signaturebox,  # Include only for visible signatures
        "sigandcertify": sigandcertify,
    }
    return dct

def sign_pdf(pdf_data, dct, p12pk, p12pc, p12oc):
    """Sign the PDF using the provided signature dictionary and certificate."""
    signed_pdf_data = pdf.cms.sign(pdf_data, dct, p12pk, p12pc, p12oc, 'sha256')
    return signed_pdf_data
