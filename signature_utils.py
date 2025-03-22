# signature_utils.py

from endesive import pdf

def prepare_signature_dict(txn_id, sigpage, signature_details, signaturebox, sigandcertify):
    """Prepare the signature dictionary for signing."""
    dct = {
        "sigfield": f"MX Signer Server {txn_id}",
        "sigpage": sigpage,
        "contact": "N/A",
        "signature": signature_details,
        "signaturebox": signaturebox,  # Include only for visible signatures
        "sigandcertify": sigandcertify,
    }
    return dct

def sign_pdf(pdf_data, dct, p12pk, p12pc, p12oc):
    """Sign the PDF using the provided signature dictionary and certificate."""
    signed_pdf_data = pdf.cms.sign(pdf_data, dct, p12pk, p12pc, p12oc, 'sha256')
    return signed_pdf_data
