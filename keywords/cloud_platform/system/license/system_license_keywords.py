from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class SystemLicenseKeywords(BaseKeyword):
    """
    System License Keywords class
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSH Connection object
        """
        self.ssh_connection = ssh_connection

    def system_license_install(self, license_file: str, sudo: bool = False) -> str:
        """
        Install the license file on the system

        Args:
            license_file(str): The path + filename where the license file is located (ex: /home/sysadmin/wrslicense-wrcp-2603.lic)
            sudo (bool): flag to check if it needs to be run as sudo.

        Returns:
            str: The output of the system license-install command
        """
        base_cmd = f"system license-install {license_file}"
        cmd = source_openrc(base_cmd)
        if sudo:
            output = self.ssh_connection.send_as_sudo(cmd)
        else:
            output = self.ssh_connection.send(cmd, get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        output = [line.strip() for line in output if line.strip()]
        output = output[0] if output else ""
        return output
