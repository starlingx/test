"""Module for the 'system host-lvg' command keywords."""

from framework.logging.automation_logger import get_logger
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

    def system_host_lvg_modify(self, host_id: str, lvg_name: str, lvm_function: str = None, lvm_pool_size: int = None) -> SystemHostLvgShowOutput:
        """
        Run 'system host-lvg-modify' to set the LVM function and/or thin pool size on a local volume group.

        The '-s' option sets the thin pool size (in GiB) when the volume group is provisioned as a
        thin lvm-csi pool on cgts-vg. A thin pool can only be grown, never shrunk.

        Args:
            host_id (str): name or id of the host (e.g. 'controller-0').
            lvg_name (str): name or uuid of the local volume group (e.g. 'cgts-vg').
            lvm_function (str): optional LVM function to assign (e.g. 'lvm-csi'). Defaults to none.
            lvm_pool_size (int): optional thin pool size in GiB to set via '-s'. Defaults to none.

        Returns:
            SystemHostLvgShowOutput: object representing the modified lvg.
        """
        command = "system host-lvg-modify"
        if lvm_function is not None:
            command += f" -f {lvm_function}"
        if lvm_pool_size is not None:
            command += f" -s {lvm_pool_size}"
        command += f" {host_id} {lvg_name}"
        output = self.ssh_connection.send(source_openrc(command))
        self.validate_success_return_code(self.ssh_connection)
        system_host_lvg_output = SystemHostLvgShowOutput(output)
        return system_host_lvg_output

    def system_host_lvg_add(self, host_id: str, lvg_name: str, lvm_function: str | None = None, lvm_type: str | None = None) -> SystemHostLvgShowOutput:
        """
        Run 'system host-lvg-add' to create a new local volume group on a host.

        Some volume group names (e.g. 'lvm-provisioner') are only accepted when the LVM function and
        type are supplied at creation time, so 'lvm_function' and 'lvm_type' can be passed to add the
        '-f' and '-t' options.

        Args:
            host_id (str): name or id of the host (e.g. 'controller-0').
            lvg_name (str): name of the local volume group to create (e.g. 'lvm-provisioner').
            lvm_function (str | None): optional LVM function to assign at creation (e.g. 'lvm-csi'). Defaults to None.
            lvm_type (str | None): optional LVM type to assign at creation (e.g. 'thin'). Defaults to None.

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

    def wait_for_total_size_above(self, host_id: str, lvg_name: str, baseline_size_gib: float, timeout: int = 300, polling_interval: int = 10) -> None:
        """
        Wait until the volume group's total size grows above the given baseline.

        After a physical volume is added, sysinv updates the volume group total size asynchronously,
        so callers should poll until it grows above the size captured before the addition.

        Args:
            host_id (str): name or id of the host (e.g. 'controller-0').
            lvg_name (str): name of the local volume group (e.g. 'lvm-provisioner').
            baseline_size_gib (float): the total size (GiB) captured before adding the physical volume.
            timeout (int): maximum time to wait in seconds.
            polling_interval (int): time between checks in seconds.

        Raises:
            TimeoutError: If the total size does not grow above the baseline within the timeout.
        """

        def is_total_size_increased() -> bool:
            current_total = float(self.get_system_host_lvg_show(host_id, lvg_name).get_system_host_lvg().get_total_size())
            get_logger().log_info(f"'{lvg_name}' on {host_id} total size is {current_total} GiB (baseline {baseline_size_gib} GiB).")
            return current_total > baseline_size_gib

        validate_equals_with_retry(is_total_size_increased, True, f"'{lvg_name}' on {host_id} total size to grow above {baseline_size_gib} GiB", timeout=timeout, polling_sleep_time=polling_interval)

    def system_host_lvg_modify_with_error(self, host_id: str, lvg_name: str, lvm_function: str = None, lvm_pool_size: int = None) -> str:
        """
        Run 'system host-lvg-modify' allowing errors, for negative testing.

        Runs the command without validating the return code and returns the raw output (which may
        contain a rejection message such as 'It's not possible to reduce the size of a thin pool').

        Args:
            host_id (str): name or id of the host (e.g. 'controller-0').
            lvg_name (str): name or uuid of the local volume group (e.g. 'cgts-vg').
            lvm_function (str): optional LVM function to assign (e.g. 'lvm-csi'). Defaults to none.
            lvm_pool_size (int): optional thin pool size in GiB to set via '-s'. Defaults to none.

        Returns:
            str: raw CLI output (may contain the error/rejection message).
        """
        command = "system host-lvg-modify"
        if lvm_function is not None:
            command += f" -f {lvm_function}"
        if lvm_pool_size is not None:
            command += f" -s {lvm_pool_size}"
        command += f" {host_id} {lvg_name}"
        output = self.ssh_connection.send(source_openrc(command))
        return "\n".join(output) if isinstance(output, list) else output
