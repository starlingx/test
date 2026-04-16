from framework.logging.automation_logger import get_logger
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
