"""Neutron agent snapshot object."""


class NeutronAgentSnapshotObject:
    """Represents a Neutron agent state in a snapshot."""

    def __init__(self):
        """Initialize NeutronAgentSnapshotObject."""
        self._host = ""
        self._binary = ""
        self._alive = False

    def get_host(self) -> str:
        """Get the host name.

        Returns:
            str: Host name.
        """
        return self._host

    def set_host(self, host: str) -> None:
        """Set the host name.

        Args:
            host (str): Host name.
        """
        self._host = host

    def get_binary(self) -> str:
        """Get the agent binary name.

        Returns:
            str: Agent binary (e.g. 'neutron-dhcp-agent').
        """
        return self._binary

    def set_binary(self, binary: str) -> None:
        """Set the agent binary name.

        Args:
            binary (str): Agent binary.
        """
        self._binary = binary

    def get_alive(self) -> bool:
        """Get whether the agent is alive.

        Returns:
            bool: True if agent is alive.
        """
        return self._alive

    def set_alive(self, alive: bool) -> None:
        """Set whether the agent is alive.

        Args:
            alive (bool): True if agent is alive.
        """
        self._alive = alive
