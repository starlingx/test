"""Network agent keywords via OpenStack SDK."""

from typing import List

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.base_keyword import BaseKeyword

from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from keywords.openstack.resources.services.object.network_agent_list_output import NetworkAgentListOutput


class NetworkAgentKeywords(BaseKeyword):
    """Query and validation operations for Neutron network agents via OpenStack SDK."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize NetworkAgentKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    def list_network_agents(self) -> NetworkAgentListOutput:
        """List all Neutron network agents.

        Returns:
            NetworkAgentListOutput: Parsed agent collection.
        """
        raw_agents = [a.to_dict() for a in self.openstack_connection.get_network().agents()]
        return NetworkAgentListOutput(raw_agents)

    def validate_network_agents_alive(self, hosts: List[str] = None) -> None:
        """Validate that all network agents are alive.

        If hosts is provided, validates only agents on those hosts.
        Otherwise validates all agents are alive.

        Args:
            hosts (List[str]): Optional list of hostnames to check.
                If None, validates all network agents.

        Raises:
            AssertionError: If any targeted network agent is not alive.
        """
        agent_output = self.list_network_agents()
        agent_output.log_agent_table()
        agents = agent_output.get_agents()

        if hosts:
            agents = [a for a in agents if a.get_host() in hosts]

        for agent in agents:
            get_logger().log_info(
                f"  {agent.get_binary()} | {agent.get_host()} | alive={agent.get_is_alive()}"
            )
            validate_equals(
                agent.get_is_alive(), True, f"{agent.get_binary()} on '{agent.get_host()}' alive"
            )
