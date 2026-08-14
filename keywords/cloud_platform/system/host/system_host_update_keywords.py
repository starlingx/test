"""Keywords for the 'system host-update' command."""

from typing import Dict

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class SystemHostUpdateKeywords(BaseKeyword):
    """Keywords for modifying host attributes via 'system host-update'."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def system_host_update(self, hostname: str, attributes: Dict[str, str]) -> None:
        """Update one or more host attributes.

        Runs: system host-update <hostname> key1=value1 key2=value2 ...

        Common attributes:
            - clock_synchronization: 'ntp' or 'ptp'
            - location: free-form location string
            - personality: host personality

        Args:
            hostname (str): Host to update.
            attributes (Dict[str, str]): Key-value pairs to set on the host.

        Raises:
            ValueError: If no attributes are provided.
            AssertionError: If the command fails.
        """
        if not attributes:
            raise ValueError("At least one attribute key=value pair is required")

        attr_str = " ".join(f"{key}={value}" for key, value in attributes.items())
        cmd = source_openrc(f"system host-update {hostname} {attr_str}")
        self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)

    def set_clock_synchronization(self, hostname: str, mode: str) -> None:
        """Set the clock synchronization mode for a host.

        Args:
            hostname (str): Host to update.
            mode (str): Clock sync mode ('ntp' or 'ptp').
        """
        self.system_host_update(hostname, {"clock_synchronization": mode})

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: String representation of SystemHostUpdateKeywords.
        """
        return "SystemHostUpdateKeywords"
