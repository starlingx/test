from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.controllerfs.objects.system_controllerfs_output import SystemControllerFSOutput


class SystemControllerFSKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system controllerfs-list' commands.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Constructor for SystemControllerFSKeywords.

        Args:
            ssh_connection (SSHConnection): An active SSH connection to the target system,
                used for executing system commands.
        """
        self.ssh_connection = ssh_connection

    def get_system_controllerfs_list(self) -> SystemControllerFSOutput:
        """
        Gets the system controllerfs list.

        Returns:
            SystemControllerFSOutput: The list of controller file systems.
        """
        command = source_openrc("system controllerfs-list")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_controllerfs_output = SystemControllerFSOutput(output)
        return system_controllerfs_output

    def system_host_controllerfs_add(self, fs_name: str, fs_size: int):
        """
        Run the "system host-controllerfs-add" command with the specified arguments.

        Args:
            fs_name (str): Name of ControllerFS Name to be added
            fs_size (int): Size of Float Name to be added

        Returns: None
        """
        self.ssh_connection.send(source_openrc(f"system controllerfs-add {fs_name}-float={fs_size}"))
        self.validate_success_return_code(self.ssh_connection)
