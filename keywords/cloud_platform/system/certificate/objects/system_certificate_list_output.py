"""System Certificate List Output Parser."""

from typing import List, Union

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.certificate.objects.system_certificate_object import SystemCertificateObject


class SystemCertificateListOutput:
    """Parser for system certificate-list command output."""

    def __init__(self, command_output: Union[str, List[str]]):
        """Initialize certificate list output parser.

        Args:
            command_output (Union[str, List[str]]): Raw command output from system certificate-list.
        """
        self.certificates = []
        content = "\n".join(command_output) if isinstance(command_output, list) else command_output

        current_cert = None
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("+---"):
                continue
            if ":" not in line:
                # Certificate name
                if current_cert:
                    self.certificates.append(current_cert)
                current_cert = SystemCertificateObject(line)
            elif current_cert:
                # Certificate property
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key == "Issuer":
                    current_cert.set_issuer(value)
                elif key == "Subject":
                    current_cert.set_subject(value)
                elif key == "Renewal":
                    current_cert.set_renewal(value)
                elif key == "File Path":
                    current_cert.set_file_path(value)

        if current_cert:
            self.certificates.append(current_cert)

    def get_certificates(self) -> List[SystemCertificateObject]:
        """Get all parsed certificates.

        Returns:
            List[SystemCertificateObject]: List of certificate objects.
        """
        return self.certificates

    def get_certificate_by_name(self, name: str) -> SystemCertificateObject:
        """Get certificate by name.

        Args:
            name (str): Certificate name to search for.

        Returns:
            SystemCertificateObject: Certificate object with matching name.

        Raises:
            KeywordException: If certificate with specified name not found.
        """
        for cert in self.certificates:
            if cert.get_name() == name:
                return cert
        raise KeywordException(f"Certificate '{name}' not found")

    def get_platform_ca_certificate(self) -> SystemCertificateObject:
        """Get platform CA certificate (self-signed root).

        When multiple copies exist (e.g., kubernetes-root-ca and ssl_ca_* in
        /opt/platform/config), they are identical certificates. This method
        prefers /etc/kubernetes/pki/ as the canonical Kubernetes location.

        Returns:
            SystemCertificateObject: Platform CA certificate.

        Raises:
            KeywordException: If platform CA not found.
        """
        matches = []
        for cert in self.certificates:
            if cert.is_self_signed() and cert.get_issuer() == "CN=starlingx":
                path = cert.get_file_path() or ""
                if "/etc/kubernetes/pki/" in path:
                    return cert
                matches.append(cert)

        if not matches:
            raise KeywordException("Platform CA certificate not found")

        return matches[0]
