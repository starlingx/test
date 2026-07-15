from framework.logging.automation_logger import get_logger
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

    def system_license_install_reject(self, license_file: str, sudo: bool = False) -> str:
        """
        Attempt to install a license file expecting the command to be rejected.

        This method is used for negative testing scenarios where the license file
        is invalid or corrupt and the system is expected to reject the installation.
        Note: The system license-install command may return exit code 0 even when
        rejecting an invalid license, reporting the error only in the output text.

        Args:
            license_file (str): The path + filename where the license file is located.
            sudo (bool): flag to check if it needs to be run as sudo.

        Returns:
            str: The output of the system license-install command for validation by the caller.
        """
        base_cmd = f"system license-install {license_file}"
        cmd = source_openrc(base_cmd)
        get_logger().log_info(f"Attempting license install expecting rejection: {license_file}")
        if sudo:
            output = self.ssh_connection.send_as_sudo(cmd)
        else:
            output = self.ssh_connection.send(cmd, get_pty=True)
        output = [line.strip() for line in output if line.strip()]
        output = " ".join(output) if output else ""
        get_logger().log_info(f"License install output: {output}")
        return output
