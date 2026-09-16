"""Module for the 'system host-lvg' command keywords."""

from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_lvg_output import SystemHostLvgOutput
from keywords.cloud_platform.system.host.objects.system_host_lvg_show_output import SystemHostLvgShowOutput


class SystemHostLvgKeywords(BaseKeyword):
    """This class contains all the keywords related to the 'system host-lvg' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initialize the SystemHostLvgKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def get_system_host_lvg_list(self, host_id: str) -> SystemHostLvgOutput:
        """
        Get the system host-lvg-list.

        Args:
            host_id (str): name or id of the host.

        Returns:
            SystemHostLvgOutput: object with the list of host-lvg.
        """
        command = source_openrc(f"system host-lvg-list {host_id}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_lvg_output = SystemHostLvgOutput(output)
        return system_host_lvg_output

    def get_system_host_lvg_show(self, host_id: str, lvg_name: str) -> SystemHostLvgShowOutput:
        """
        Get the system host-lvg-show.

        Args:
            host_id (str): name or id of the host.
            lvg_name (str): name or uuid of lvg.

        Returns:
            SystemHostLvgShowOutput: object representing the lvg.
        """
        command = source_openrc(f"system host-lvg-show {host_id} {lvg_name}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_lvg_output = SystemHostLvgShowOutput(output)
        return system_host_lvg_output

    def system_host_lvg_modify(self, host_id: str, lvg_name: str, lvm_function: str) -> SystemHostLvgShowOutput:
        """
        Run 'system host-lvg-modify' to set the LVM function on a local volume group.

        Args:
            host_id (str): name or id of the host (e.g. 'controller-0').
            lvg_name (str): name or uuid of the local volume group (e.g. 'cgts-vg').
            lvm_function (str): the LVM function to assign (e.g. 'lvm-csi').

        Returns:
            SystemHostLvgShowOutput: object representing the modified lvg.
        """
        command = source_openrc(f"system host-lvg-modify -f {lvm_function} {host_id} {lvg_name}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_lvg_output = SystemHostLvgShowOutput(output)
        return system_host_lvg_output

    def system_host_lvg_add(self, host_id: str, lvg_name: str, lvm_function: str = None, lvm_type: str = None) -> SystemHostLvgShowOutput:
        """
        Run 'system host-lvg-add' to create a new local volume group on a host.

        Some volume group names (e.g. 'lvm-provisioner') are only accepted when the LVM function and
        type are supplied at creation time, so 'lvm_function' and 'lvm_type' can be passed to add the
        '-f' and '-t' options.

        Args:
            host_id (str): name or id of the host (e.g. 'controller-0').
            lvg_name (str): name of the local volume group to create (e.g. 'lvm-provisioner').
            lvm_function (str): optional LVM function to assign at creation (e.g. 'lvm-csi'). Defaults to none.
            lvm_type (str): optional LVM type to assign at creation (e.g. 'thin'). Defaults to none.

        Returns:
            SystemHostLvgShowOutput: object representing the created lvg.
        """
        command = f"system host-lvg-add {host_id} {lvg_name}"
        if lvm_function is not None:
            command += f" -f {lvm_function}"
        if lvm_type is not None:
            command += f" -t {lvm_type}"
        output = self.ssh_connection.send(source_openrc(command))
        self.validate_success_return_code(self.ssh_connection)
        system_host_lvg_output = SystemHostLvgShowOutput(output)
        return system_host_lvg_output

    def system_host_lvg_delete(self, host_id: str, lvg_name: str) -> None:
        """
        Run 'system host-lvg-delete' to remove a local volume group from a host.

        Args:
            host_id (str): name or id of the host (e.g. 'controller-0').
            lvg_name (str): name or uuid of the local volume group to delete (e.g. 'lvm-provisioner').
        """
        command = source_openrc(f"system host-lvg-delete {host_id} {lvg_name}")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

    def wait_for_thin_cur_lv_zero(self, host_id: str, lvg_name: str, timeout: int = 300, polling_interval: int = 10) -> None:
        """
        Wait until 'system host-lvg-show' reports 'thin_cur_lv' as 0 for the given volume group.

        After a PVC is deleted, sysinv updates its 'thin_cur_lv' count asynchronously (and lags
        behind the actual LVM state). The volume group's lvm-csi function cannot be removed while
        sysinv still counts provisioned thin logical volumes, so callers should wait for this before
        running 'host-lvg-modify -f none'. A value that is absent/unknown (None) does not count as 0,
        so it keeps polling until a real 0 is observed or the timeout is reached.

        Args:
            host_id (str): name or id of the host (e.g. 'controller-0').
            lvg_name (str): name of the local volume group (e.g. 'cgts-vg').
            timeout (int): maximum time to wait in seconds.
            polling_interval (int): time between checks in seconds.

        Raises:
            TimeoutError: If 'thin_cur_lv' does not reach 0 within the timeout.
        """

        def get_thin_cur_lv() -> int:
            return self.get_system_host_lvg_show(host_id, lvg_name).get_system_host_lvg().get_thin_cur_lv()

        # get_thin_cur_lv() returns None when the value is unknown; 'None == 0' is False, so an
        # unknown value never satisfies the check and polling continues until a real 0 or timeout.
        validate_equals_with_retry(get_thin_cur_lv, 0, f"'{lvg_name}' on {host_id} thin_cur_lv to reach 0", timeout=timeout, polling_sleep_time=polling_interval)
