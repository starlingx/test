import shlex

from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.ca_certificate.objects.system_ca_certificate_list_output import SystemCaCertificateListOutput
from keywords.cloud_platform.system.ca_certificate.objects.system_ca_certificate_show_output import SystemCaCertificateShowOutput


class SystemCaCertificatesKeywords(BaseKeyword):
    """
    Class for System ca-certificates Keywords
    """

    def __init__(self, ssh_connection: object) -> None:
        """
        Constructor.

        Args:
            ssh_connection (object): SSH connection object
        """
        self.ssh_connection = ssh_connection

    def ca_certificate_install(self, certificate_path: str) -> SystemCaCertificateShowOutput:
        """
        Executes the system wide installation of a certificate from a file.

        This method returns upon the completion of the 'system ca-certificate-install'

        Args:
            certificate_path (str): The absolute path of the certificate on the system.

        Returns:
            SystemCaCertificateShowOutput: an object representing status and values related to the installed certificate

        """
        output = self.ssh_connection.send(source_openrc(f"system ca-certificate-install {shlex.quote(certificate_path)}"))
        self.validate_success_return_code(self.ssh_connection)
        ca_certificate_install_output = SystemCaCertificateShowOutput(output)

        return ca_certificate_install_output

    def ca_certificate_show(self, uuid: str) -> SystemCaCertificateShowOutput:
        """
        Shows the status and values for a specific certificate.

        This method returns upon the completion of the 'system ca-certificate-show'

        Args:
            uuid (str): The String value of the uuid of the certificate being shown

        Returns:
            SystemCaCertificateShowOutput: an object representing status and values related to the certificate

        """
        output = self.ssh_connection.send(source_openrc(f"system ca-certificate-show {shlex.quote(uuid)}"))
        self.validate_success_return_code(self.ssh_connection)
        ca_certificate_show = SystemCaCertificateShowOutput(output)

        return ca_certificate_show

    def ca_certificate_list(self) -> SystemCaCertificateListOutput:
        """
        Shows the list of installed certificates.

        This method returns upon the completion of the 'system ca-certificate-list'

        Returns:
            SystemCaCertificateListOutput: A list of certificates objects

        """
        output = self.ssh_connection.send(source_openrc("system ca-certificate-list"))
        self.validate_success_return_code(self.ssh_connection)
        ca_certificate_list = SystemCaCertificateListOutput(output)

        return ca_certificate_list

    def ca_certificate_uninstall(self, uuid: str) -> str:
        """
        Uninstalls a specific certificate from the system.

        This method returns upon the completion of the 'system ca-certificate-uninstall'

        Args:
            uuid (str): The String of the uuid of the certificate being uninstalled.

        Returns:
            str: the raw output of the certificate being uninstalled
        """
        output = self.ssh_connection.send(source_openrc(f"system ca-certificate-uninstall {shlex.quote(uuid)}"))
        self.validate_success_return_code(self.ssh_connection)
        return output
