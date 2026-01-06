from typing import Union

from keywords.cloud_platform.security.objects.ipsec_certificate_object import IPSecCertificateObject


class IPSecCertificateOutput:
    """Parser for certificate command output (subject/issuer or MD5)."""

    def __init__(self, command_output: Union[str, list[str]], cert_type: str, hostname: str, cert_path: str):
        """Initialize certificate output parser.

        Args:
            command_output (Union[str, list[str]]): Raw command output.
            cert_type (str): Type of certificate (key, cert, ica, root, k8s_cert).
            hostname (str): Hostname where certificate is located.
            cert_path (str): Path to certificate file.
        """
        self.raw_output = command_output if isinstance(command_output, list) else [str(command_output)]

        # Auto-detect output type and create appropriate object
        if self._is_subject_issuer_output():
            subject, issuer = self._extract_subject_issuer()
            self.cert_object = IPSecCertificateObject(cert_type, hostname, cert_path, subject=subject, issuer=issuer)
        else:
            md5_hash = self._extract_md5()
            self.cert_object = IPSecCertificateObject(cert_type, hostname, cert_path, md5_hash=md5_hash)

    def _is_subject_issuer_output(self) -> bool:
        """Check if output contains subject/issuer information.

        Returns:
            bool: True if output contains subject/issuer data.
        """
        return any("subject=" in str(line) or "issuer=" in str(line) for line in self.raw_output)

    def _extract_subject_issuer(self) -> tuple[str, str]:
        """Extract subject and issuer from command output.

        Returns:
            tuple[str, str]: Subject and issuer information.
        """
        subject = ""
        issuer = ""

        for line in self.raw_output:
            line = line.strip()
            if line.startswith("subject="):
                subject = line.replace("subject=", "").strip()
            elif line.startswith("issuer="):
                issuer = line.replace("issuer=", "").strip()

        return subject, issuer

    def _extract_md5(self) -> str:
        """Extract MD5 hash from command output.

        Returns:
            str: Extracted MD5 hash.
        """
        for line in self.raw_output:
            if "MD5(" in line or line.startswith("MD5 "):
                if "=" in line:
                    parts = line.split("=")
                    if len(parts) > 1:
                        return parts[-1].strip()
                else:
                    parts = line.split()
                    if len(parts) > 1:
                        return parts[-1].strip()
        return ""

    def get_certificate(self) -> IPSecCertificateObject:
        """Get certificate object.

        Returns:
            IPSecCertificateObject: Certificate object with parsed information.
        """
        return self.cert_object
