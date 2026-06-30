"""Network agent list output parsing and manipulation."""

from typing import Dict, List

from framework.logging.automation_logger import get_logger

from keywords.openstack.resources.services.object.network_agent_object import NetworkAgentObject


class NetworkAgentListOutput:
    """Parses and provides access to a collection of NetworkAgentObjects."""

    def __init__(self, raw_agents: List[Dict]) -> None:
        """Initialize NetworkAgentListOutput from raw agent dicts.

        Args:
            raw_agents (List[Dict]): List of agent dictionaries from OpenStack SDK.
        """
        self._agents = []
        for raw in raw_agents:
            agent = NetworkAgentObject()
            agent.set_id(raw.get("id", ""))
            agent.set_binary(raw.get("binary", ""))
            agent.set_host(raw.get("host", ""))
            agent.set_agent_type(raw.get("agent_type", ""))
            agent.set_is_alive(raw.get("is_alive", False))
            agent.set_is_admin_state_up(raw.get("is_admin_state_up", raw.get("admin_state_up", False)))
            agent.set_availability_zone(raw.get("availability_zone", ""))
            self._agents.append(agent)

    def get_agents(self) -> List[NetworkAgentObject]:
        """Get all network agent objects.

        Returns:
            List[NetworkAgentObject]: List of agent objects.
        """
        return self._agents

    def get_agents_by_binary(self, binary: str) -> List[NetworkAgentObject]:
        """Get all agents matching the binary name.

        Args:
            binary (str): Agent binary (e.g. 'neutron-dhcp-agent').

        Returns:
            List[NetworkAgentObject]: List of matching agents.
        """
        return [a for a in self._agents if a.get_binary() == binary]

    def get_agents_by_host(self, host: str) -> List[NetworkAgentObject]:
        """Get all agents running on a specific host.

        Args:
            host (str): Host name (e.g. 'controller-0').

        Returns:
            List[NetworkAgentObject]: List of matching agents.
        """
        return [a for a in self._agents if a.get_host() == host]

    def get_dead_agents(self) -> List[NetworkAgentObject]:
        """Get all agents that are not alive.

        Returns:
            List[NetworkAgentObject]: List of dead agents.
        """
        return [a for a in self._agents if not a.get_is_alive()]

    def log_agent_table(self) -> None:
        """Log the full network agent list as a formatted table."""
        get_logger().log_info("Network Agent List:")
        get_logger().log_info(
            f"  {'Binary':<30} {'Host':<25} {'Alive':<7} {'Admin Up':<10} {'Agent Type'}"
        )
        get_logger().log_info(f"  {'-' * 100}")
        for agent in self._agents:
            get_logger().log_info(
                f"  {agent.get_binary():<30} {agent.get_host():<25} "
                f"{str(agent.get_is_alive()):<7} {str(agent.get_is_admin_state_up()):<10} "
                f"{agent.get_agent_type()}"
            )

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return f"NetworkAgentListOutput(count={len(self._agents)})"
