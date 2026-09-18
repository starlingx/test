"""Module for the 'system host-pv' command keywords."""

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_disk_object import SystemHostDiskObject
from keywords.cloud_platform.system.host.objects.system_host_pv_output import SystemHostPvOutput
from keywords.cloud_platform.system.host.objects.system_host_pv_show_output import SystemHostPvShowOutput


class SystemHostPvKeywords(BaseKeyword):
    """This class contains all the keywords related to the 'system host-pv' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initialize the SystemHostPvKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def get_system_host_pv_list(self, host_id: str) -> SystemHostPvOutput:
        """
        Get the system host-pv-list.

        Args:
            host_id (str): name or id of the host.

        Returns:
            SystemHostPvOutput: object with the list of host-pv.
        """
        command = source_openrc(f"system host-pv-list {host_id}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_lvg_output = SystemHostPvOutput(output)
        return system_host_lvg_output

    def get_system_host_pv_show(self, host_id: str, uuid: str) -> SystemHostPvShowOutput:
        """
        Get the system host-pv-show.

        Args:
            host_id (str): name or id of the host.
            uuid (str): uuid of pv.

        Returns:
            SystemHostPvShowOutput: object representing the pv.
        """
        command = source_openrc(f"system host-pv-show {host_id} {uuid}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_pv_output = SystemHostPvShowOutput(output)
        return system_host_pv_output

    def system_host_pv_add(self, host_id: str, lvg_name: str, disk: str) -> SystemHostPvShowOutput:
        """
        Add a physical volume (disk) to a local volume group.

        Args:
            host_id (str): name or id of the host (e.g. 'controller-0').
            lvg_name (str): name of the local volume group (e.g. 'lvm-provisioner').
            disk (str): the disk device path or uuid to add as a physical volume.

        Returns:
            SystemHostPvShowOutput: object representing the created physical volume.
        """
        command = source_openrc(f"system host-pv-add {host_id} {lvg_name} {disk}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_pv_output = SystemHostPvShowOutput(output)
        return system_host_pv_output

    def find_and_add_free_pv(self, host_id: str, lvg_name: str, disks: list) -> SystemHostDiskObject:
        """
        Add the first of the given disks that can be added as a physical volume to a volume group.

        Tries to add each disk to the volume group with 'system host-pv-add', stopping as soon as
        one succeeds. A disk that cannot be added (e.g. it is already in use) is skipped and the next
        one is tried, mirroring the OSD add flow.

        Args:
            host_id (str): name or id of the host (e.g. 'controller-0').
            lvg_name (str): name of the local volume group (e.g. 'lvm-provisioner').
            disks (list): SystemHostDiskObject candidates to try, in preference order.

        Returns:
            SystemHostDiskObject: the disk that was successfully added as a physical volume.

        Raises:
            KeywordException: If none of the given disks could be added as a physical volume.
        """
        for disk in disks:
            device_path = disk.get_device_path()
            try:
                get_logger().log_info(f"Trying to add disk {device_path} as a physical volume to '{lvg_name}' on {host_id}.")
                self.system_host_pv_add(host_id, lvg_name, device_path)
                return disk
            except AssertionError:
                get_logger().log_info(f"Disk {device_path} could not be added to '{lvg_name}', trying the next disk.")

        raise KeywordException(f"No disk could be added as a physical volume to '{lvg_name}' on {host_id}. All candidates failed.")

    def system_host_pv_delete(self, host_id: str, pv_uuid: str) -> None:
        """
        Delete a physical volume from a local volume group.

        Args:
            host_id (str): name or id of the host (e.g. 'controller-0').
            pv_uuid (str): uuid of the physical volume to delete.
        """
        command = source_openrc(f"system host-pv-delete {host_id} {pv_uuid}")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
