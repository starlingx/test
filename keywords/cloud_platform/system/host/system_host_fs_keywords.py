import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_fs_output import SystemHostFSOutput
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


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

    def system_host_fs_modify(self, hostname: str, fs_name: str, fs_size: int = None, functions: str = None):
        """
        Run the "system host-fs-modify" command with the specified arguments.

        Args:
            hostname (str): Name of the host to modify.
            fs_name (str): Name of FS Name to be modified
            fs_size (int, optional): Size of FS Name to be modified
            functions (str, optional): Functions to set for the filesystem

        Returns: None
        """
        command = f"system host-fs-modify {hostname} {fs_name}"

        if fs_size is not None:
            command += f"={fs_size}"

        if functions is not None:
            command += f" --functions={functions}"

        self.ssh_connection.send(source_openrc(command))
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

    def needs_host_fs_grow(self, hostname: str, fs_name: str, target_size: int) -> bool:
        """
        Check whether a host filesystem must grow to reach a target size.

        'system host-fs-modify' only accepts a size strictly greater than the current
        one — a value equal to or below the current size is rejected, not a no-op. This
        answers the "is there room / is it already allocated" question before any modify,
        so a grow step can be made idempotent.

        Args:
            hostname (str): Host whose filesystem is checked.
            fs_name (str): Host-fs name, for example "docker" or "kubelet".
            target_size (int): Desired minimum size in GiB.

        Returns:
            bool: True when the filesystem exists and its current size is below
                target_size (a grow is needed and allowed). False when the filesystem
                is already at or above target_size (already allocated — skip).

        Raises:
            ValueError: When the host has no filesystem named fs_name.
        """
        fs = self.get_system_host_fs_list(hostname).get_host_fs(fs_name)
        if fs is None:
            raise ValueError(f"Host '{hostname}' has no filesystem named '{fs_name}'")
        current_size = fs.get_size()
        if current_size >= target_size:
            get_logger().log_info(f"{hostname}: '{fs_name}' already {current_size} GiB (>= target {target_size}) — no grow needed")
            return False
        get_logger().log_info(f"{hostname}: '{fs_name}' is {current_size} GiB (< target {target_size}) — grow needed")
        return True

    def grow_host_fs_to(self, hostname: str, fs_name: str, target_size: int, timeout: int = 300, poll_interval: int = 15) -> None:
        """
        Grow one host filesystem to a target size, idempotently.

        If the filesystem is already at or above target_size, this is a no-op (safe to
        re-run). Otherwise it issues a single 'system host-fs-modify' and waits for the
        filesystem to settle out of the transient 'Modifying' state. The settled steady
        state is 'In-Use' (not 'Ready'), so this waits for any non-'Modifying' state
        rather than matching a specific settled string. The grow is online and needs no
        host lock or reboot.

        Args:
            hostname (str): Host whose filesystem is grown.
            fs_name (str): Host-fs name, for example "docker" or "kubelet".
            target_size (int): Desired minimum size in GiB.
            timeout (int): Seconds to wait for the resize to settle.
            poll_interval (int): Seconds between state polls.

        Raises:
            ValueError: When the host has no filesystem named fs_name.
        """
        if not self.needs_host_fs_grow(hostname, fs_name, target_size):
            return

        get_logger().log_info(f"{hostname}: growing '{fs_name}' to {target_size} GiB")
        self.system_host_fs_modify(hostname, fs_name, target_size)
        # The settled steady state after a grow is 'In-Use' (not 'Ready'). Reuse the
        # existing wait_for_fs_state keyword with that state.
        self.wait_for_fs_state(hostname, fs_name, expected_state="In-Use", timeout=timeout, sleep_time=poll_interval)

    def wait_for_fs_state(self, hostname: str, fs_name: str, expected_state: str = "Ready", timeout: int = 300, sleep_time: int = 30) -> None:
        """
        Wait until the given FS on the host reaches the expected state.

        Args:
            hostname (str): Host name to check
            fs_name (str): FS name to wait for
            expected_state (str): Expected state to wait for. Defaults to "Ready".
            timeout (int): Max time in seconds to wait
            sleep_time (int): Interval between checks

        Raises:
            TimeoutError: If FS does not reach expected state within timeout

        Returns:
            None: This function does not return any value
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            fs_output = self.get_system_host_fs_list(hostname)
            fs = fs_output.get_host_fs(fs_name)
            if fs and fs.get_state() == expected_state:
                return
            time.sleep(sleep_time)
        raise TimeoutError(f"FS '{fs_name}' on host '{hostname}' did not reach '{expected_state}' state within {timeout} seconds")

    def get_hosts_without_monitor(self) -> list[str]:
        """
        Return a list of hosts that do NOT have a monitor.

        Returns:
            list[str]: List of hostnames without monitor
        """
        no_monitor_hosts = []

        all_hosts = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_controllers_and_computes()

        for host in all_hosts:
            fs_output = self.get_system_host_fs_list(host.get_host_name())
            if not fs_output.has_monitor():
                no_monitor_hosts.append(host.get_host_name())

        return no_monitor_hosts
