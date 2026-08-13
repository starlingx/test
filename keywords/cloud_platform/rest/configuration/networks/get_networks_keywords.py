"""Keywords for GetNetworksKeywords."""

from framework.rest.rest_response import RestResponse
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.configuration.networks.objects.network_output import NetworkOutput
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class GetNetworksKeywords(BaseKeyword):
    """Keywords for /networks REST API operations."""

    def __init__(self):
        """Initialize GetNetworksKeywords with configuration URL."""
        self.base_url = GetRestUrlKeywords().get_configuration_url()

    def get_networks(self) -> NetworkOutput:
        """Get networks from REST API.

        Returns:
            NetworkOutput: Parsed output.
        """
        response = CloudRestClient().get(f"{self.base_url}/networks")
        self.validate_success_status_code(response)
        return NetworkOutput(response)

    def get_networks_with_error(self, resource_id: str = "") -> RestResponse:
        """Get /networks with invalid ID expecting error.

        Args:
            resource_id (str): The resource ID (may be invalid).

        Returns:
            RestResponse: The raw response for error validation.
        """
        url = f"{self.base_url}/networks/{resource_id}" if resource_id else f"{self.base_url}/networks"
        response = CloudRestClient().get(url)
        return response

    def get_networks_no_auth(self, resource_id: str = "") -> RestResponse:
        """Get /networks without authentication.

        Args:
            resource_id (str): The resource ID.

        Returns:
            RestResponse: The raw response for auth validation.
        """
        url = f"{self.base_url}/networks/{resource_id}" if resource_id else f"{self.base_url}/networks"
        response = CloudRestClient().get(url, auth=False)
        return response
