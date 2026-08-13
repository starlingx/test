"""Keywords for LLDP REST API operations."""

from framework.rest.rest_response import RestResponse
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.configuration.lldp.objects.lldp_agent_output import LldpAgentOutput
from keywords.cloud_platform.rest.configuration.lldp.objects.lldp_neighbour_output import LldpNeighbourOutput
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class GetLldpKeywords(BaseKeyword):
    """Keywords for LLDP REST API operations."""

    def __init__(self):
        """Initialize GetLldpKeywords with configuration URL."""
        self.base_url = GetRestUrlKeywords().get_configuration_url()

    def get_lldp_agents(self) -> LldpAgentOutput:
        """Get LLDP agents from REST API.

        Returns:
            LldpAgentOutput: Parsed output.
        """
        response = CloudRestClient().get(f"{self.base_url}/lldp_agents")
        self.validate_success_status_code(response)
        return LldpAgentOutput(response)

    def get_lldp_neighbours(self) -> LldpNeighbourOutput:
        """Get LLDP neighbours from REST API.

        Returns:
            LldpNeighbourOutput: Parsed output.
        """
        response = CloudRestClient().get(f"{self.base_url}/lldp_neighbours")
        self.validate_success_status_code(response)
        return LldpNeighbourOutput(response)

    def get_lldp_agents_with_error(self, resource_id: str) -> RestResponse:
        """Get LLDP agent with invalid ID.

        Args:
            resource_id (str): The resource ID.

        Returns:
            RestResponse: The raw response.
        """
        response = CloudRestClient().get(f"{self.base_url}/lldp_agents/{resource_id}")
        return response

    def get_lldp_neighbours_with_error(self, resource_id: str) -> RestResponse:
        """Get LLDP neighbour with invalid ID.

        Args:
            resource_id (str): The resource ID.

        Returns:
            RestResponse: The raw response.
        """
        response = CloudRestClient().get(f"{self.base_url}/lldp_neighbours/{resource_id}")
        return response

    def get_lldp_agents_no_auth(self, resource_id: str) -> RestResponse:
        """Get LLDP agent without auth.

        Args:
            resource_id (str): The resource ID.

        Returns:
            RestResponse: The raw response.
        """
        response = CloudRestClient().get(f"{self.base_url}/lldp_agents/{resource_id}", auth=False)
        return response

    def get_lldp_neighbours_no_auth(self, resource_id: str) -> RestResponse:
        """Get LLDP neighbour without auth.

        Args:
            resource_id (str): The resource ID.

        Returns:
            RestResponse: The raw response.
        """
        response = CloudRestClient().get(f"{self.base_url}/lldp_neighbours/{resource_id}", auth=False)
        return response
