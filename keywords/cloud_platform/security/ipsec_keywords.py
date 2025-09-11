from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.security.objects.ipsec_certificate_output import IPSecCertificateOutput
from keywords.cloud_platform.security.objects.ipsec_dnsmasq_output import IPSecDnsmasqOutput
from keywords.cloud_platform.security.objects.ipsec_security_association_output import IPSecSecurityAssociationOutput
from keywords.cloud_platform.system.show.system_show_keywords import SystemShowKeywords
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

    def get_security_associations(self) -> IPSecSecurityAssociationOutput:
        """Get IPSec security associations using swanctl command.

        Returns:
            IPSecSecurityAssociationOutput: Parsed security associations.
        """
        cmd = "swanctl --list-sa"
        output = self.ssh_connection.send_as_sudo(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return IPSecSecurityAssociationOutput(output)

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

    def validate_service_name_is_valid(self, service_name: str) -> None:
        """Validate that the IPSec service name is valid.

        Args:
            service_name (str): Service name to validate (ipsec-server, ipsec).

        Raises:
            KeywordException: If service name is not valid.
        """
        valid_services = ["ipsec-server", "ipsec"]
        if service_name not in valid_services:
            raise KeywordException(f"Invalid service_name '{service_name}'. Valid services: {valid_services}")

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
