from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_stor_output import SystemHostStorageOutput


class SystemHostStorageKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-stor-*' commands.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): An active SSH connection to the target system,
                used for executing system commands.
        """
        self.ssh_connection = ssh_connection

    def get_system_host_stor_list(self, hostname: str) -> SystemHostStorageOutput:
        """
        Retrieve the storage list for a specific system host.

        Executes the `system host-stor-list` command for the given hostname and
        returns the parsed result as a `SystemHostStorageOutput` object.

        Args:
            hostname (str): The name of the host for which to retrieve the storage list.

        Returns:
            SystemHostStorageOutput: An object containing the parsed list of storages for the specified host.

        Raises:
            AssertionError: If the command execution does not return a successful status.
        """
        output = self.ssh_connection.send(source_openrc(f"system host-stor-list --nowrap {hostname}"))
        self.validate_success_return_code(self.ssh_connection)
        system_host_storage_output = SystemHostStorageOutput(output)

        return system_host_storage_output

    def system_host_stor_add(self, hostname: str, disk_uuids: list) -> None:
        """
        Attempts to add the first available OSD disk to the specified host.

        Iterates through the provided list of disk UUIDs and tries to add each one as an OSD
        to the given host using the 'system host-stor-add' command. The method stops as soon
        as one disk is successfully added. If all attempts fail, it raises a RuntimeError.

        Args:
            hostname (str): The name of the host where the OSD should be added.
            disk_uuids (list): A list of disk UUIDs to try adding as OSDs.

        Raises:
            RuntimeError: If none of the disk UUIDs could be successfully added as OSD.
        """
        success = False

        for disk_uuid in disk_uuids:

            try:
                self.ssh_connection.send(source_openrc(f"system host-stor-add {hostname} osd {disk_uuid}"))
                self.validate_success_return_code(self.ssh_connection)
                success = True
                break
            except AssertionError:
                continue

        if not success:
            raise RuntimeError("Failed to add any OSD disk. All attempts were unsuccessful.")
