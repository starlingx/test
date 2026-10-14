"""Unit tests for IPSecCertificateOutput MD5 parsing and matching.

Covers the key-type-agnostic public-key MD5 comparison and the regression where
an ECDSA key passed to `openssl rsa -modulus` produced the MD5 of empty input,
which must not be treated as a valid hash or a false match.
"""

from keywords.cloud_platform.security.objects.ipsec_certificate_output import IPSecCertificateOutput

# openssl public-key DER MD5 of a matching key/cert pair (same value on both sides).
SAMPLE_MATCHING_PUBKEY_MD5 = ["MD5(stdin)= baf59ff7f5b05fde6799439b6f31a290"]

# Real output captured when `openssl rsa -modulus` was run against an ECDSA key:
# openssl writes "Not an RSA key" to stderr and nothing to stdout, so `openssl md5`
# hashes empty input and returns the well-known empty-input MD5.
SAMPLE_ECDSA_RSA_MODULUS_FAILURE = [
    "Not an RSA key",
    "MD5(stdin)= d41d8cd98f00b204e9800998ecf8427e",
]

# Subject/issuer output, which must be detected as a DN pair rather than an MD5.
SAMPLE_SUBJECT_ISSUER_OUTPUT = [
    "subject=CN=ipsec-controller-0",
    "issuer=CN=StarlingX-Intermediate-CA, O=StarlingX",
]


def test_valid_pubkey_md5_is_parsed():
    """A normal MD5 line is parsed into the certificate object."""
    output = IPSecCertificateOutput(SAMPLE_MATCHING_PUBKEY_MD5, "cert_md5", "controller-0", "/path.crt")
    cert = output.get_certificate()

    assert cert.get_md5_hash() == "baf59ff7f5b05fde6799439b6f31a290"
    assert cert.has_valid_md5() is True


def test_empty_input_md5_is_rejected():
    """The MD5 of empty input (failed openssl pipeline) is treated as no hash."""
    output = IPSecCertificateOutput(SAMPLE_ECDSA_RSA_MODULUS_FAILURE, "key_md5", "controller-0", "/path.key")
    cert = output.get_certificate()

    assert cert.get_md5_hash() == ""
    assert cert.has_valid_md5() is False


def test_matching_md5_hashes_match():
    """Two identical non-empty public-key hashes compare equal."""
    key_output = IPSecCertificateOutput(SAMPLE_MATCHING_PUBKEY_MD5, "key_md5", "controller-0", "/path.key")
    cert_output = IPSecCertificateOutput(SAMPLE_MATCHING_PUBKEY_MD5, "cert_md5", "controller-0", "/path.crt")

    assert key_output.get_certificate().matches_md5(cert_output.get_certificate().get_md5_hash()) is True


def test_empty_hashes_do_not_falsely_match():
    """Two failed (empty) hashes must NOT be reported as a match."""
    key_output = IPSecCertificateOutput(SAMPLE_ECDSA_RSA_MODULUS_FAILURE, "key_md5", "controller-0", "/path.key")
    cert_output = IPSecCertificateOutput(SAMPLE_ECDSA_RSA_MODULUS_FAILURE, "cert_md5", "controller-0", "/path.crt")

    assert key_output.get_certificate().matches_md5(cert_output.get_certificate().get_md5_hash()) is False


def test_subject_issuer_output_detected():
    """Subject/issuer output is detected and parsed, not treated as an MD5."""
    output = IPSecCertificateOutput(SAMPLE_SUBJECT_ISSUER_OUTPUT, "subject_issuer", "controller-0", "/path.crt")
    cert = output.get_certificate()

    assert cert.get_subject() == "CN=ipsec-controller-0"
    assert cert.get_issuer() == "CN=StarlingX-Intermediate-CA, O=StarlingX"
    assert cert.has_valid_md5() is False
