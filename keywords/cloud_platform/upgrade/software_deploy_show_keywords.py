from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.upgrade.objects.software_deploy_show_output import SoftwareDeployShowOutput


class SoftwareDeployShowKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'software deploy show' command.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Instance of the class.

        Args:
            ssh_connection(SSHConnection): An instance of an SSH connection.

        """
        self.ssh_connection = ssh_connection

    def get_software_deploy_show(self, sudo: bool = False, timeout: int = 300) -> SoftwareDeployShowOutput:
        """
        Get the software deploy show output

        Args:
            sudo(bool):  flag to check if it needs to be run as sudo.
            timeout(int): timeout waiting for command to return
        Returns:
            SoftwareDeployShowOutput: Object with software deploy show command output

        """
        base_cmd = "software deploy show"
        cmd = source_openrc(base_cmd)

        if sudo:
            output = self.ssh_connection.send_as_sudo(cmd, reconnect_timeout=timeout)
        else:
            output = self.ssh_connection.send(cmd, reconnect_timeout=timeout, get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        software_deploy_show_output = SoftwareDeployShowOutput(output)

        return software_deploy_show_output
