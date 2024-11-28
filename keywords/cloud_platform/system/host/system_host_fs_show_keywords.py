from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_fs_show_output import SystemHostFSShowOutput


class SystemHostFSShowKeywords(BaseKeyword):
    """
    Provides methods to interact with the system host filesystem
    using given SSH connection.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """
        Initializes the SystemHostFSShowKeywords with an SSH connection.

        Args:
            ssh_connection: An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def get_system_host_fs_show(self, host_id: str, fs_uuid: str) -> SystemHostFSShowOutput:
        """
        Retrieves information about a specific filesystem on a host.

        Args:
            host_id (str): The identifier of the host.
            fs_uuid (str): The UUID of the filesystem.

        Returns:
            SystemHostFSShowOutput: Output object containing details about the filesystem.

        Raises:
            KeywordException: If the parsed output is invalid or missing required fields.
        """
        command = source_openrc(f'system host-fs-show {host_id} {fs_uuid}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_fs_output = SystemHostFSShowOutput(output)
        return system_host_fs_output
