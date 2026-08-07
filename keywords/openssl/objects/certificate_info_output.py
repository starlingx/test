from typing import Union

from keywords.openssl.objects.certificate_info_object import CertificateInfoObject


class CertificateInfoOutput:
    """Parser for openssl x509 certificate information output.

    Parses the combined output of:
        openssl x509 -noout -subject -issuer -serial
    """

    def __init__(self, command_output: Union[str, list[str]]):
        """Initialize certificate info output parser.

        Args:
            command_output (Union[str, list[str]]): Raw command output from
                openssl x509 -noout -subject -issuer -serial.
        """
        raw = "\n".join(command_output) if isinstance(command_output, list) else command_output
        self._cert_info = self._parse(raw)

    def _parse(self, raw: str) -> CertificateInfoObject:
        """Parse raw openssl output into a CertificateInfoObject.

        Args:
            raw (str): Raw output string.

        Returns:
            CertificateInfoObject: Parsed certificate information.
        """
        subject = ""
        issuer = ""
        serial = ""
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("subject="):
                subject = stripped.split("=", 1)[1].strip()
            elif stripped.lower().startswith("issuer="):
                issuer = stripped.split("=", 1)[1].strip()
            elif stripped.lower().startswith("serial="):
                serial = stripped.split("=", 1)[1].strip()
        return CertificateInfoObject(subject=subject, issuer=issuer, serial=serial)

    def get_certificate_info(self) -> CertificateInfoObject:
        """Get the parsed certificate info object.

        Returns:
            CertificateInfoObject: Object with subject, issuer, and serial.
        """
        return self._cert_info
