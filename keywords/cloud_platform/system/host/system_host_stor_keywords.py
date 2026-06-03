import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_stor_output import SystemHostStorageOutput
from keywords.cloud_platform.system.host.system_host_disk_keywords import SystemHostDiskKeywords


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

    def system_host_stor_add(self, hostname: str, disk_uuids: list) -> str:
        """
        Attempts to add the first available OSD disk to the specified host.

        Iterates through the provided list of disk UUIDs and tries to add each one as an OSD
        to the given host using the 'system host-stor-add' command. The method stops as soon
        as one disk is successfully added. If all attempts fail, it raises a RuntimeError.

        Args:
            hostname (str): The name of the host where the OSD should be added.
            disk_uuids (list): A list of disk UUIDs to try adding as OSDs.

        Returns:
            str: The UUID of the newly created OSD.

        Raises:
            RuntimeError: If none of the disk UUIDs could be successfully added as OSD.
        """
        for disk_uuid in disk_uuids:
            try:
                output = self.ssh_connection.send(source_openrc(f"system host-stor-add {hostname} osd {disk_uuid}"))
                self.validate_success_return_code(self.ssh_connection)
                stor_output = SystemHostStorageOutput(output, is_vertical_table=True)
                osd_uuids = stor_output.get_all_osd_uuids()
                if not osd_uuids:
                    raise KeywordException(f"host-stor-add succeeded for disk {disk_uuid} on {hostname} but no UUID was returned.")
                return osd_uuids[0]
            except AssertionError:
                continue

        raise RuntimeError("Failed to add any OSD disk. All attempts were unsuccessful.")

    def system_stor_add_specific_disk(self, hostname: str, disk_uuid: str) -> None:
        """
        Add OSD to specific disk to the specified host.

        Args:
            hostname (str): The name of the host which the OSD should be added on.
            disk_uuid (str): A string of disk UUID to add OSD.

        """
        self.ssh_connection.send(source_openrc(f"system host-stor-add {hostname} osd {disk_uuid}"))
        self.validate_success_return_code(self.ssh_connection)

    def system_host_stor_delete(self, osd_uuid: str, force_delete: bool = False) -> None:
        """
        Attempts to delete OSD.

        Args:
            osd_uuid (str): the string of osd uuid.
            force_delete (bool): use --force option in the command

        """
        cmd = f"system host-stor-delete {osd_uuid}"
        if force_delete:
            cmd += " --force"
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

    def find_and_add_osd(self, hostnames: list[str]) -> tuple[str, str]:
        """
        Find a host with an available disk and add an OSD on it.

        For each host, gets all disks, filters out those already used as OSD,
        and attempts to add an OSD on the remaining candidates.

        Args:
            hostnames (list[str]): Ordered list of hostnames to try.

        Returns:
            tuple[str, str]: A tuple of (hostname, osd_uuid).

        Raises:
            KeywordException: If no OSD could be added on any host.
        """
        host_disk_keywords = SystemHostDiskKeywords(self.ssh_connection)

        for hostname in hostnames:
            get_logger().log_info(f"Trying to add OSD on {hostname}")
            all_disk_uuids = host_disk_keywords.get_system_host_disk_list(hostname).get_all_uuid() or []
            existing_osd_disk_uuids = self.get_system_host_stor_list(hostname).get_host_all_osd_idisk_uuid()
            candidate_disks = [uuid for uuid in all_disk_uuids if uuid not in existing_osd_disk_uuids]

            if candidate_disks:
                try:
                    osd_uuid = self.system_host_stor_add(hostname, candidate_disks)
                    get_logger().log_info(f"Successfully added OSD {osd_uuid} on {hostname}")
                    return hostname, osd_uuid
                except RuntimeError:
                    get_logger().log_info(f"No available disk could be added on {hostname}, trying next host.")

        raise KeywordException("Failed to add OSD on any host. All attempts were unsuccessful.")

    def wait_for_all_osd_cleared_on_host(self, host_name: str, timeout: int = 600) -> bool:
        """
        Wait for all OSDs to be cleared from host-stor-list

        Args:
            host_name (str): hostname
            timeout (int): the amount of time in seconds to wait

        Returns:
            bool: True if all OSDs are deleted

        """
        osd_status_timeout = time.time() + timeout

        while time.time() < osd_status_timeout:
            current_osd_uuids = self.get_system_host_stor_list(host_name).get_all_osd_uuids()
            if not current_osd_uuids:
                return True
            time.sleep(10)

        raise KeywordException("OSDs were not deleted completely.")
