import time

from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.security.objects.ipsec_certificate_output import IPSecCertificateOutput
from keywords.cloud_platform.security.objects.ipsec_dnsmasq_output import IPSecDnsmasqOutput
from keywords.cloud_platform.security.objects.ipsec_security_association_output import IPSecSecurityAssociationOutput
from keywords.cloud_platform.system.show.system_show_keywords import SystemShowKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManager
from keywords.files.file_keywords import FileKeywords


class IPSecKeywords(BaseKeyword):
    """Keywords for IPSec operations and validations.

    This class provides methods for managing IPSec certificates,
    security associations, and service status validation.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize IPSec keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection
        # Initialize reusable keyword classes
        self.file_keywords = FileKeywords(ssh_connection)
        self.system_show = SystemShowKeywords(ssh_connection)

    def get_dnsmasq_hosts(self) -> IPSecDnsmasqOutput:
        """Get dnsmasq.hosts file content.

        Returns:
            IPSecDnsmasqOutput: Parsed dnsmasq.hosts content.
        """
        system_show_object = self.system_show.system_show().get_system_show_object()
        software_version = system_show_object.get_software_version()
        dnsmasq_path = f"/opt/platform/config/{software_version}/dnsmasq.hosts"
        output = self.ssh_connection.send(f"cat {dnsmasq_path}")
        self.validate_success_return_code(self.ssh_connection)
        return IPSecDnsmasqOutput(output)

    def get_security_associations(self, stable_count: int = 3, interval: int = 2, timeout: int = 60) -> IPSecSecurityAssociationOutput:
        """Get IPSec security associations, waiting until the count stabilizes.

        Polls until the association count is identical across consecutive polls
        to ensure the full output buffer has been captured.

        Args:
            stable_count (int): Number of consecutive identical counts required before returning.
            interval (int): Seconds to wait between polls.
            timeout (int): Maximum seconds to wait before raising an exception.

        Returns:
            IPSecSecurityAssociationOutput: Parsed security associations.

        Raises:
            KeywordException: If the count does not stabilize within the timeout.
        """
        consecutive = 0
        last_count = -1
        last_output = None
        timeout_time = time.time() + timeout

        while time.time() < timeout_time:
            output = self.ssh_connection.send_as_sudo("swanctl --list-sa")
            self.validate_success_return_code(self.ssh_connection)
            parsed = IPSecSecurityAssociationOutput(output)
            current_count = len(parsed.get_associations())

            if current_count == last_count:
                consecutive += 1
            else:
                consecutive = 1
                last_count = current_count
                last_output = output

            if consecutive >= stable_count:
                return IPSecSecurityAssociationOutput(last_output)

            time.sleep(interval)

        raise KeywordException(f"Security associations did not stabilize within {timeout} seconds")

    def get_certificate_info_by_type(self, cert_type: str) -> IPSecCertificateOutput:
        """Get certificate information by certificate type with automatic path resolution.

        Args:
            cert_type (str): Certificate type (root_ca, ica_l1, ica).

        Returns:
            IPSecCertificateOutput: Certificate output with requested information.
        """
        valid_types = ["root_ca", "ica_l1", "ica"]
        if cert_type not in valid_types:
            raise KeywordException(f"Invalid cert_type '{cert_type}'. Valid types: {valid_types}")

        cert_path = None
        if cert_type == "ica_l1":
            cert_path = "x509ca/system-local-ca-1_l1.crt"
        elif cert_type == "ica":
            cert_path = "x509ca/system-local-ca-1.crt"
        elif cert_type == "root_ca":
            cert_path = "x509ca/system-root-ca-1.crt"

        full_primary_path = f"/etc/swanctl/{cert_path}"

        # Use FileKeywords to check if file exists
        if not self.file_keywords.validate_file_exists_with_sudo(full_primary_path):
            cert_path = "x509ca/system-root-ca-1.crt"  # Fallback to root_ca
            full_primary_path = f"/etc/swanctl/{cert_path}"

        return self.get_certificate_info_subject_issuer(full_primary_path)

    def get_certificate_info_subject_issuer(self, cert_path: str) -> IPSecCertificateOutput:
        """Get certificate subject and issuer information.

        Args:
            cert_path (str): Path to the certificate file.

        Returns:
            IPSecCertificateOutput: Certificate output with subject/issuer information.
        """
        cmd = f"openssl x509 -in {cert_path} -noout -subject -issuer"
        output = self.ssh_connection.send_as_sudo(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return IPSecCertificateOutput(output, "subject_issuer", "active_controller", cert_path)

    def get_certificate_info_cert_md5(self, cert_path: str) -> IPSecCertificateOutput:
        """Get certificate MD5 hash.

        Args:
            cert_path (str): Path to the certificate file.

        Returns:
            IPSecCertificateOutput: Certificate output with MD5 hash.
        """
        cmd = f"openssl x509 -in {cert_path} -modulus -noout | openssl md5"
        output = self.ssh_connection.send_as_sudo(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return IPSecCertificateOutput(output, "cert_md5", "active_controller", cert_path)

    def get_certificate_info_key_md5(self, cert_path: str) -> IPSecCertificateOutput:
        """Get certificate key MD5 hash.

        Args:
            cert_path (str): Path to the certificate key file.

        Returns:
            IPSecCertificateOutput: Certificate output with key MD5 hash.
        """
        cmd = f"openssl rsa -in {cert_path} -modulus -noout | openssl md5"
        output = self.ssh_connection.send_as_sudo(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return IPSecCertificateOutput(output, "key_md5", "active_controller", cert_path)

    def get_ipsec_service_name(self) -> str:
        """Get the correct IPSec service name based on OS version.

        In Trixie (strongSwan 6.0), ipsec.service was replaced by strongswan.service.
        In Bullseye (strongSwan 5.9), the service is named ipsec.

        Returns:
            str: Service name ('strongswan' for Trixie, 'ipsec' for Bullseye).
        """
        return "strongswan" if CloudPlatformVersionManager.is_trixie(self.ssh_connection) else "ipsec"

    def validate_service_name_is_valid(self, service_name: str) -> bool:
        """Check if the IPSec service name is valid.

        Args:
            service_name (str): Service name to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        return service_name in ["ipsec-server", "ipsec", "strongswan"]

    def get_ipsec_certificate_path(self, hostname: str) -> str:
        """Get full IPSec certificate path for hostname.

        Args:
            hostname (str): Hostname for certificate.

        Returns:
            str: Full certificate path.
        """
        return f"/etc/swanctl/x509/system-ipsec-certificate-{hostname}.crt"

    def get_ipsec_key_path(self, hostname: str) -> str:
        """Get full IPSec key path for hostname.

        Args:
            hostname (str): Hostname for key.

        Returns:
            str: Full key path.
        """
        return f"/etc/swanctl/private/system-ipsec-certificate-{hostname}.key"
