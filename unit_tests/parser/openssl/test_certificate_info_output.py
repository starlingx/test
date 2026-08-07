"""Unit tests for CertificateInfoOutput parser."""

from keywords.openssl.objects.certificate_info_output import CertificateInfoOutput


SAMPLE_OUTPUT_STRING = (
    "subject=CN = test-cert.example.com\n"
    "issuer=CN = EJBCA-Sub-CA, O = StarlingX\n"
    "serial=0A1B2C3D4E5F\n"
)

SAMPLE_OUTPUT_LIST = [
    "subject=CN = test-cert.example.com",
    "issuer=CN = EJBCA-Sub-CA, O = StarlingX",
    "serial=0A1B2C3D4E5F",
]


def test_parse_string_output():
    """Tests parsing when output is a string."""
    parser = CertificateInfoOutput(SAMPLE_OUTPUT_STRING)
    cert = parser.get_certificate_info()

    assert cert.get_subject() == "CN = test-cert.example.com"
    assert cert.get_issuer() == "CN = EJBCA-Sub-CA, O = StarlingX"
    assert cert.get_serial() == "0A1B2C3D4E5F"


def test_parse_list_output():
    """Tests parsing when output is a list of lines."""
    parser = CertificateInfoOutput(SAMPLE_OUTPUT_LIST)
    cert = parser.get_certificate_info()

    assert cert.get_subject() == "CN = test-cert.example.com"
    assert cert.get_issuer() == "CN = EJBCA-Sub-CA, O = StarlingX"
    assert cert.get_serial() == "0A1B2C3D4E5F"


def test_self_signed_detection():
    """Tests self-signed certificate detection."""
    output = "subject=CN = My CA\nissuer=CN = My CA\nserial=01\n"
    cert = CertificateInfoOutput(output).get_certificate_info()

    assert cert.is_self_signed() is True


def test_not_self_signed():
    """Tests non-self-signed certificate."""
    cert = CertificateInfoOutput(SAMPLE_OUTPUT_STRING).get_certificate_info()

    assert cert.is_self_signed() is False


def test_empty_output():
    """Tests parser with empty input."""
    cert = CertificateInfoOutput("").get_certificate_info()

    assert cert.get_subject() == ""
    assert cert.get_issuer() == ""
    assert cert.get_serial() == ""


def test_empty_list_output():
    """Tests parser with empty list input."""
    cert = CertificateInfoOutput([]).get_certificate_info()

    assert cert.get_subject() == ""
    assert cert.get_issuer() == ""
    assert cert.get_serial() == ""
