from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


class LabConnectionHolder:
    """
    Class that can hold multiple SSH connections to various nodes in a lab.

    This object is used to pass SSH connections to mid-level keywords.
    """

    def __init__(self) -> None:
        """
        Constructor

        """
        self.active_controller_ssh = None
        self.standby_controller_ssh = None
        self.compute_ssh = []
        self.hostname_to_ssh_dict = {}

    def set_active_controller_ssh(self, ssh_connection: SSHConnection) -> None:
        """
        Set the connection to the active controller

        Args:
            ssh_connection (SSHConnection): Connection to the active controller

        """
        # The active controller is often set by the floating IP, and its name isn't always taken note of.
        self.active_controller_ssh = ssh_connection
        active_controller_name = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

        self.hostname_to_ssh_dict[active_controller_name] = ssh_connection

    def set_standby_controller_ssh(self, ssh_connection: SSHConnection) -> None:
        """
        Set the connection to the standby controller

        Args:
            ssh_connection (SSHConnection): Connection to the standby controller

        """
        if not ssh_connection.get_name():
            raise ValueError("This standby controller SSH connection doesn't have a name")

        self.standby_controller_ssh = ssh_connection
        self.hostname_to_ssh_dict[ssh_connection.get_name()] = ssh_connection

    def set_compute_ssh(self, ssh_connection: SSHConnection) -> None:
        """
        Set a connection to a compute host

        Args:
            ssh_connection (SSHConnection): Connection to the standby controller

        """
        if not ssh_connection.get_name():
            raise ValueError("This compute SSH connection doesn't have a name")

        self.compute_ssh.append(ssh_connection)
        self.hostname_to_ssh_dict[ssh_connection.get_name()] = ssh_connection

    def get_active_controller_ssh(self) -> SSHConnection:
        """
        This function will return the SSH Connection associated with the active controller.

        Returns:
            SSHConnection: active controller

        """
        if not self.active_controller_ssh:
            raise ValueError("There is no active controller ssh in the lab_connection_holder")

        return self.active_controller_ssh

    def get_standby_controller_ssh(self) -> SSHConnection:
        """
        This function will return the SSH Connection associated with the standby controller.

        Returns:
            SSHConnection: standby controller

        """
        if not self.standby_controller_ssh:
            raise ValueError("There is no standby controller ssh in the lab_connection_holder")

        return self.standby_controller_ssh

    def get_host_ssh(self, host_name: str) -> SSHConnection:
        """
        This function will return the SSH Connection associated with the host of the specified host_name

        Args:
            host_name (str): Name of the host

        Returns:
            SSHConnection: Connection to the specified host.

        """
        if host_name not in self.hostname_to_ssh_dict:
            raise ValueError(f"There is no host named {host_name} in the lab_connection_holder")

        return self.hostname_to_ssh_dict[host_name]
