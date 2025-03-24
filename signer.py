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
