"""Network agent object representation."""


class NetworkAgentObject:
    """Represents a single Neutron network agent."""

    def __init__(self) -> None:
        """Initialize an empty NetworkAgentObject."""
        self._id = ""
        self._binary = ""
        self._host = ""
        self._agent_type = ""
        self._is_alive = False
        self._is_admin_state_up = False
        self._availability_zone = ""

    def get_id(self) -> str:
        """Get the agent ID.

        Returns:
            str: Agent UUID.
        """
        return self._id

    def set_id(self, agent_id: str) -> None:
        """Set the agent ID.

        Args:
            agent_id (str): Agent UUID.
        """
        self._id = agent_id

    def get_binary(self) -> str:
        """Get the agent binary name.

        Returns:
            str: Agent binary (e.g. 'neutron-dhcp-agent', 'neutron-l3-agent').
        """
        return self._binary

    def set_binary(self, binary: str) -> None:
        """Set the agent binary name.

        Args:
            binary (str): Agent binary name.
        """
        self._binary = binary

    def get_host(self) -> str:
        """Get the agent host.

        Returns:
            str: Host name (e.g. 'controller-0').
        """
        return self._host

    def set_host(self, host: str) -> None:
        """Set the agent host.

        Args:
            host (str): Host name.
        """
        self._host = host

    def get_agent_type(self) -> str:
        """Get the agent type.

        Returns:
            str: Agent type (e.g. 'DHCP agent', 'L3 agent', 'Open vSwitch agent').
        """
        return self._agent_type

    def set_agent_type(self, agent_type: str) -> None:
        """Set the agent type.

        Args:
            agent_type (str): Agent type.
        """
        self._agent_type = agent_type

    def get_is_alive(self) -> bool:
        """Get whether the agent is alive.

        Returns:
            bool: True if the agent is alive.
        """
        return self._is_alive

    def set_is_alive(self, is_alive: bool) -> None:
        """Set whether the agent is alive.

        Args:
            is_alive (bool): True if the agent is alive.
        """
        self._is_alive = is_alive

    def get_is_admin_state_up(self) -> bool:
        """Get whether the agent admin state is up.

        Returns:
            bool: True if admin state is up.
        """
        return self._is_admin_state_up

    def set_is_admin_state_up(self, is_admin_state_up: bool) -> None:
        """Set whether the agent admin state is up.

        Args:
            is_admin_state_up (bool): True if admin state is up.
        """
        self._is_admin_state_up = is_admin_state_up

    def get_availability_zone(self) -> str:
        """Get the availability zone.

        Returns:
            str: Availability zone.
        """
        return self._availability_zone

    def set_availability_zone(self, availability_zone: str) -> None:
        """Set the availability zone.

        Args:
            availability_zone (str): Availability zone.
        """
        self._availability_zone = availability_zone

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return (
            f"NetworkAgentObject(binary={self._binary}, host={self._host}, "
            f"alive={self._is_alive}, admin_up={self._is_admin_state_up})"
        )
