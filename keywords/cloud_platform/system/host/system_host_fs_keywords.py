from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_fs_output import SystemHostFSOutput


class SystemHostFSKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-fs-list' command.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): ssh connection
        """
        self.ssh_connection = ssh_connection

    def get_system_host_fs_list(self, host_name: str) -> SystemHostFSOutput:
        """
        Gets the system host-fs-list <host_name>

        Args:
            host_name (str): host name

        Returns:
            SystemHostFSOutput: object with the list of host fs.
        """
        command = source_openrc(f"system host-fs-list {host_name}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_fs_output = SystemHostFSOutput(output)
        return system_host_fs_output

    def system_host_fs_add(self, hostname: str, fs_name: str, fs_size: int):
        """
        Run the "system host-fs-add" command with the specified arguments.

        Args:
            hostname (str): Name of the host to be added.
            fs_name (str): Name of FS Name to be added
            fs_size (int): Size of FS Name to be added

        Returns: None
        """
        self.ssh_connection.send(source_openrc(f"system host-fs-add {hostname} {fs_name}={fs_size}"))
        self.validate_success_return_code(self.ssh_connection)

    def system_host_fs_modify(self, hostname: str, fs_name: str, fs_size: int):
        """
        Run the "system host-fs-modify" command with the specified arguments.

        Args:
            hostname (str): Name of the host to modify.
            fs_name (str): Name of FS Name to be modified
            fs_size (int): Size of FS Name to be modified

        Returns: None
        """
        self.ssh_connection.send(source_openrc(f"system host-fs-modify {hostname} {fs_name}={fs_size}"))
        self.validate_success_return_code(self.ssh_connection)

    def system_host_fs_modify_with_error(self, hostname: str, fs_name: str, fs_size: int) -> list[str]:
        """
        Run the "system host-fs-modify" command with invalid arguments, like decreasing size

        Args:
            hostname (str): Name of the host to modify.
            fs_name (str): Name of FS Name to be modified
            fs_size (int): Size of FS Name to be modified

        Returns:
            list[str]: a list of error msg
        """
        message = self.ssh_connection.send(source_openrc(f"system host-fs-modify {hostname} {fs_name}={fs_size}"))
        return message

    def system_host_fs_delete(self, hostname: str, fs_name: str):
        """
        Run the "system host-fs-delete" command with the specified arguments.

        Args:
            hostname (str): Name of the host to be deleted.
            fs_name (str): Name of FS Name to be deleted

        Returns: None
        """
        self.ssh_connection.send(source_openrc(f"system host-fs-delete {hostname} {fs_name}"))
        self.validate_success_return_code(self.ssh_connection)
