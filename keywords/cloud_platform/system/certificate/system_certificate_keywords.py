"""System Certificate Keywords."""

import os

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.security.cat.objects.ssl_ca_certificate_output import SslCaCertificateOutput
from keywords.cloud_platform.system.certificate.objects.system_certificate_list_output import SystemCertificateListOutput
from keywords.cloud_platform.system.certificate.objects.system_certificate_show_output import SystemCertificateShowOutput
from keywords.files.file_keywords import FileKeywords


class SystemCertificateKeywords(BaseKeyword):
    """Keywords for system certificate operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize system certificate keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        self.ssh_connection = ssh_connection

    def certificate_list(self) -> SystemCertificateListOutput:
        """Execute system certificate-list command.

        Returns:
            SystemCertificateListOutput: Parsed certificate list output.
        """
        output = self.ssh_connection.send(source_openrc("system certificate-list"))
        self.validate_success_return_code(self.ssh_connection)
        return SystemCertificateListOutput(output)

    def get_ca_certificate(self) -> SslCaCertificateOutput:
        """Retrieve CA certificate from StarlingX lab controller.

        Returns:
            SslCaCertificateOutput: SSL certificate output object with base64 and raw content.
        """
        # Get canonical certificate path
        cert_list_output = self.certificate_list()
        platform_ca = cert_list_output.get_platform_ca_certificate()
        ca_cert_path = platform_ca.get_file_path()

        # Read certificate content
        file_keywords = FileKeywords(self.ssh_connection)
        cert_content = file_keywords.read_file_with_sudo(ca_cert_path)

        ssl_ca_dir = os.path.dirname(ca_cert_path)
        ca_file_name = os.path.basename(ca_cert_path)

        return SslCaCertificateOutput(cert_content, ssl_ca_dir, ca_file_name)

    def certificate_show(self, cert_name: str) -> SystemCertificateShowOutput:
        """Run system certificate-show and return parsed output.

        Args:
            cert_name (str): Certificate name (e.g., "system-local-ca", "system-restapi-gui-certificate").

        Returns:
            SystemCertificateShowOutput: Parsed certificate-show output with getters for all fields.
        """
        cmd = source_openrc(f"system certificate-show {cert_name}")
        output = self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)
        raw = "\n".join(output) if isinstance(output, list) else output
        return SystemCertificateShowOutput(raw)
