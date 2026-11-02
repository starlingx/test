from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.controllerfs.objects.system_controllerfs_output import SystemControllerFSOutput
from keywords.cloud_platform.system.controllerfs.system_controllerfs_show_keywords import SystemControllerFSShowKeywords


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

    def system_controllerfs_modify(self, fs_sizes: dict[str, int]) -> None:
        """
        Run the "system controllerfs-modify" command to modify one or more controllerfs sizes.

        Args:
            fs_sizes (dict[str, int]): Filesystem name-value pairs, e.g. {"database": 11, "platform": 11}.

        Returns:
            None: This method does not return any value.
        """
        fs_args = " ".join(f"{name}={size}" for name, size in fs_sizes.items())
        command = source_openrc(f"system controllerfs-modify {fs_args}")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

    def increase_all_controllerfs(self, controllerfs_list: SystemControllerFSOutput, increment: int = 1):
        """
        Increase the size of all controllerfs filesystems by the specified amount.

        Args:
            controllerfs_list (SystemControllerFSOutput): The current controllerfs list.
            increment (int): The amount in GiB to increase each filesystem. Defaults to 1.
        """
        new_sizes = {}
        for fs in controllerfs_list.get_filesystems():
            new_sizes[fs.get_name()] = fs.get_size() + increment

        get_logger().log_info(f"Increasing all controllerfs by {increment} GiB: {new_sizes}")
        self.system_controllerfs_modify(new_sizes)

    def needs_controllerfs_grow(self, fs_name: str, target_size: int) -> bool:
        """
        Check whether a controller (DRBD-backed) filesystem must grow to reach a target.

        'system controllerfs-modify' only accepts a size strictly greater than the
        current one — a value equal to or below current is rejected, not a no-op. This
        answers the "is there room / is it already allocated" question before any modify,
        so a grow step can be made idempotent.

        Args:
            fs_name (str): Controller filesystem name, for example "docker-distribution".
            target_size (int): Desired minimum size in GiB.

        Returns:
            bool: True when the filesystem exists and its current size is below
                target_size (grow needed and allowed). False when it is already at or
                above target_size (already allocated — skip).

        Raises:
            ValueError: When no controller filesystem named fs_name exists.
        """
        filesystems = self.get_system_controllerfs_list().get_filesystems()
        fs = next((f for f in filesystems if f.get_name() == fs_name), None)
        if fs is None:
            raise ValueError(f"No controller filesystem named '{fs_name}'")
        current_size = fs.get_size()
        if current_size >= target_size:
            get_logger().log_info(f"controllerfs '{fs_name}' already {current_size} GiB (>= target {target_size}) — no grow needed")
            return False
        get_logger().log_info(f"controllerfs '{fs_name}' is {current_size} GiB (< target {target_size}) — grow needed")
        return True

    def grow_controllerfs_to(self, fs_name: str, target_size: int, timeout: int = 900, poll_interval: int = 15) -> None:
        """
        Grow one controller (DRBD-backed) filesystem to a target size, idempotently.

        If the filesystem is already at or above target_size, this is a no-op (safe to
        re-run). Otherwise it issues a single 'system controllerfs-modify' and waits for
        the filesystem's sysinv state to reach 'available'. controllerfs-modify is
        system-wide: sysinv applies the resize to all controllers via puppet and DRBD
        sync automatically. The timeout is generous because a large delta resync on a
        busy standby controller can exceed several minutes.

        Args:
            fs_name (str): Controller filesystem name, for example "docker-distribution".
            target_size (int): Desired minimum size in GiB.
            timeout (int): Seconds to wait for the resize to settle.
            poll_interval (int): Seconds between state polls.

        Raises:
            ValueError: When no controller filesystem named fs_name exists.
        """
        if not self.needs_controllerfs_grow(fs_name, target_size):
            return

        get_logger().log_info(f"growing controllerfs '{fs_name}' to {target_size} GiB")
        self.system_controllerfs_modify({fs_name: target_size})
        self._wait_for_controllerfs_available(fs_name, timeout=timeout, poll_interval=poll_interval)

    def _wait_for_controllerfs_available(self, fs_name: str, timeout: int = 900, poll_interval: int = 15) -> None:
        """
        Wait until a controller filesystem's sysinv state reaches 'available'.

        The controllerfs list output carries no state column, so the state is read from
        'system controllerfs-show' via SystemControllerFSShowKeywords.

        Args:
            fs_name (str): Controller filesystem name being waited on.
            timeout (int): Seconds to wait for the resize to settle.
            poll_interval (int): Seconds between polls.
        """
        show_kw = SystemControllerFSShowKeywords(self.ssh_connection)

        def is_available() -> bool:
            fs = show_kw.get_system_controllerfs_show(fs_name).get_filesystems()
            state = fs.get_state()
            status = state.get_status() if state is not None else None
            get_logger().log_info(f"controllerfs '{fs_name}' status is '{status}'")
            return status == "available"

        validate_equals_with_retry(
            is_available,
            True,
            f"controllerfs '{fs_name}' reaches 'available' after the resize",
            timeout=timeout,
            polling_sleep_time=poll_interval,
        )
