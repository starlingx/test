"""System Certificate Keywords."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.certificate.objects.system_certificate_list_output import SystemCertificateListOutput


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
