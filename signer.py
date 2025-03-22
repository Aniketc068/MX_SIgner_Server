# signer.py

import re
import datetime
import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from cryptography.hazmat import backends
from cryptography.x509.oid import NameOID
from cryptography.x509.oid import ExtensionOID
from cryptography.x509 import ocsp, ExtensionOID, AuthorityInformationAccessOID
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.hashes import SHA256
from transaction_tracker import log_transaction
from cryptography.x509 import load_der_x509_crl
import pytz



def load_pfx(file_path, password, txn_id):
    """Function to load pkcs12 object from the given password-protected pfx file."""
    try:
        with open(file_path, 'rb') as fp:
            pfx_data = fp.read()
            # Try to load the PFX file
            return pkcs12.load_key_and_certificates(pfx_data, password.encode(), default_backend())
    
    except ValueError as e:
        # If ValueError is raised, it likely indicates an invalid password for the PFX file
        log_transaction(txn_id, "failure", "Invalid password for the PFX file.")
        raise ValueError("Invalid password for the PFX file.")
    
    except FileNotFoundError:
        log_transaction(txn_id, "failure", "No such PFX Found. Please Upload with using /upload")
        raise ValueError("No such PFX Found. Please Upload with using /upload")
    
    except Exception as e:
        log_transaction(txn_id, "failure", f"Error loading PFX file: {str(e)}")
        raise ValueError(f"Error loading PFX file: {str(e)}")

# Function to validate PFX certificate file extension
def validate_args(pfx_certificate, password, txn_id):
    """Validating the parameters with predefined values."""
    IS_PFX = lambda pfx_certificate: re.match(r'^(.[^,]+)(.pfx|.PFX){1}$', pfx_certificate)
    if not IS_PFX(pfx_certificate):
        log_transaction(txn_id, "failure", "Not a proper pfx file with .pfx or .PFX extension",)
        raise ValueError('Not a proper pfx file with .pfx or .PFX extension')


# Function to extract names from the PFX certificate
OID_NAMES = {
    NameOID.COMMON_NAME: 'CN',
    NameOID.COUNTRY_NAME: 'C',
    NameOID.DOMAIN_COMPONENT: 'DC',
    NameOID.EMAIL_ADDRESS: 'E',
    NameOID.GIVEN_NAME: 'G',
    NameOID.LOCALITY_NAME: 'L',
    NameOID.ORGANIZATION_NAME: 'O',
    NameOID.ORGANIZATIONAL_UNIT_NAME: 'OU',
    NameOID.SURNAME: 'SN'
}

def get_rdns_names(rdns):
    names = {}
    for oid in OID_NAMES:
        names[OID_NAMES[oid]] = ''
    for rdn in rdns:
        for attr in rdn._attributes:
            if attr.oid in OID_NAMES:
                names[OID_NAMES[attr.oid]] = attr.value
    return names

def get_cn_from_cert(rdns):
    """Extract the Common Name (CN) from the certificate's RDNs."""
    for rdn in rdns:
        for attr in rdn._attributes:
            if attr.oid == NameOID.COMMON_NAME:
                return attr.value
    return 'Unknown CN'  # Return a default if CN is not found


def load_user_cert(cert_pem):
    """ Load the user's certificate from a PEM string (or file). """
    cert = x509.load_pem_x509_certificate(cert_pem.encode('ascii'), backends.default_backend())
    return cert

def get_issuer(cert, txn_id):
    aia = cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS).value
    issuers = [ia for ia in aia if ia.access_method == AuthorityInformationAccessOID.CA_ISSUERS]
    if not issuers:
        log_transaction(txn_id, "failure", 'No issuers entry in AIA')
        raise Exception(f'No issuers entry in AIA')
    return issuers[0].access_location.value

def get_ocsp_server(cert, txn_id):
    aia = cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS).value
    ocsps = [ia for ia in aia if ia.access_method == AuthorityInformationAccessOID.OCSP]
    if not ocsps:
        log_transaction(txn_id, "failure", 'No OCSP server entry in AIA')
        raise Exception(f'No OCSP server entry in AIA')
    return ocsps[0].access_location.value

def get_issuer_cert(ca_issuer, txn_id):
    try:
        # Fetch issuer certificate
        response = requests.get(ca_issuer)
        issuer_pem = response.text

        if issuer_pem.startswith("-----BEGIN CERTIFICATE-----"):
            try:
                return x509.load_pem_x509_certificate(issuer_pem.encode('utf-8'), backends.default_backend())
            except ValueError as pem_e:
                log_transaction(txn_id, "failure", f'Error loading PEM issuer cert: {str(pem_e)}')
                raise Exception(f"Error loading PEM issuer cert: {str(pem_e)}")
        else:
            issuer_der = response.content
            return x509.load_der_x509_certificate(issuer_der, backends.default_backend())
    except Exception as e:
        log_transaction(txn_id, "failure", f'Error fetching or parsing issuer certificate: {str(e)}')
        print(f"Error fetching or parsing issuer certificate: {str(e)}")
        raise

def get_ocsp_cert_status(ocsp_server, cert, issuer_cert, txn_id):
    """ Get the certificate status from the OCSP server. """
    builder = ocsp.OCSPRequestBuilder()
    builder = builder.add_certificate(cert, issuer_cert, SHA256())
    req = builder.build()
    
    request_data = req.public_bytes(serialization.Encoding.DER)
    headers = {'Content-Type': 'application/ocsp-request'}
    response = requests.post(ocsp_server, data=request_data, headers=headers)

    if response.ok:
        try:
            ocsp_decoded = ocsp.load_der_ocsp_response(response.content)
            if ocsp_decoded.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL:
                certificate_status = ocsp_decoded.certificate_status
                if certificate_status == ocsp.OCSPCertStatus.REVOKED:
                    log_transaction(txn_id, "failure", 'The certificate is revoked From OCSP. Signing aborted. Please try another Valid certificate for signing.')
                    raise Exception("The certificate is revoked From OCSP. Signing aborted. Please try another Valid certificate for signing.")  # Stop the signing process here
                else:
                    return certificate_status
            else:
                log_transaction(txn_id, "failure", f'Decoding OCSP response failed: {ocsp_decoded.response_status}')
                raise Exception(f'Decoding OCSP response failed: {ocsp_decoded.response_status}')
        except Exception as e:
          
            raise
    else:
        log_transaction(txn_id, "failure", f'Fetching OCSP cert status failed with response status: {response.status_code}')
        raise Exception(f'Fetching OCSP cert status failed with response status: {response.status_code}')
    

def fetch_crl(certificate, txn_id):
    """ Fetch the CRL associated with the given certificate. """
    try:
        # Check if the CRL Distribution Points extension exists
        crl_ext = certificate.extensions.get_extension_for_oid(ExtensionOID.CRL_DISTRIBUTION_POINTS)
        crl_urls = []
        for dp in crl_ext.value:
            for gn in dp.full_name:
                crl_urls.append(gn.value)

        if not crl_urls:
            log_transaction(txn_id, "failure", 'No CRL Distribution Points found in the certificate.')
            print("No CRL Distribution Points found in the certificate.")
            return None

        # Fetch and parse the CRL from the first URL
        print(f"Fetching CRL from: {crl_urls[0]}")
        response = requests.get(crl_urls[0])
        response.raise_for_status()  # Raise exception for HTTP errors

        crl = load_der_x509_crl(response.content, default_backend())
        return crl
    except Exception as e:
        log_transaction(txn_id, "failure", f'Error fetching CRL: {e}')
        print(f"Error fetching CRL: {e}")
        return None

def check_if_revoked(cert, crl):
    """ Check if the certificate is revoked by comparing serial numbers with the CRL. """
    serial_number = cert.serial_number
    for revoked_cert in crl:
        if revoked_cert.serial_number == serial_number:
            return True
    return False


def check_certificate_expiry(cert, txn_id):
    """ Check if the certificate has expired, considering IST (Indian Standard Time). """
    current_time_utc = datetime.datetime.now(datetime.timezone.utc)
    ist_timezone = pytz.timezone('Asia/Kolkata')
    current_time_ist = current_time_utc.astimezone(ist_timezone)
    
    # Convert cert's not_valid_after to aware datetime in IST
    cert_expiry_ist = cert.not_valid_after.replace(tzinfo=pytz.utc).astimezone(ist_timezone)

    if cert_expiry_ist < current_time_ist:
        log_transaction(txn_id, "failure", 'The certificate is Expired. Signing aborted. Please try another valid certificate for signing.')
        raise Exception("The certificate is Expired. Signing aborted. Please try another valid certificate for signing.") 
    

def validate_key_usage(certificate, txn_id):
    """
    Validates if the certificate has Digital Signature key usage.
    Raises an exception if the required key usage is not present.
    """
    try:
        key_usage = certificate.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE).value
        if not key_usage.digital_signature:
            log_transaction(txn_id, "failure", 'The certificate is Not Digital Signature key_usage. Signing aborted. Please try another valid certificate for signing.')
            raise Exception("The certificate is Not Digital Signature key_usage. Signing aborted. Please try another valid certificate for signing.")
    except Exception as e:
        log_transaction(txn_id, "failure", f'Error validating key usage: {e}')
        raise Exception(f"Error validating key usage: {e}")
