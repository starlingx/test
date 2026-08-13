"""Keywords for GetServicenodesKeywords."""

from framework.rest.rest_response import RestResponse
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.configuration.servicenodes.objects.servicenode_output import ServicenodeOutput
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class GetServicenodesKeywords(BaseKeyword):
    """Keywords for /servicenodes REST API operations."""

    def __init__(self):
        """Initialize GetServicenodesKeywords with configuration URL."""
        self.base_url = GetRestUrlKeywords().get_configuration_url()

    def get_inodes(self) -> ServicenodeOutput:
        """Get inodes from REST API.

        Returns:
            ServicenodeOutput: Parsed output.
        """
        response = CloudRestClient().get(f"{self.base_url}/servicenodes")
        self.validate_success_status_code(response)
        return ServicenodeOutput(response)

    def get_inodes_with_error(self, resource_id: str = "") -> RestResponse:
        """Get /servicenodes with invalid ID expecting error.

        Args:
            resource_id (str): The resource ID (may be invalid).

        Returns:
            RestResponse: The raw response for error validation.
        """
        url = f"{self.base_url}/servicenodes/{resource_id}" if resource_id else f"{self.base_url}/servicenodes"
        response = CloudRestClient().get(url)
        return response

    def get_inodes_no_auth(self, resource_id: str = "") -> RestResponse:
        """Get /servicenodes without authentication.

        Args:
            resource_id (str): The resource ID.

        Returns:
            RestResponse: The raw response for auth validation.
        """
        url = f"{self.base_url}/servicenodes/{resource_id}" if resource_id else f"{self.base_url}/servicenodes"
        response = CloudRestClient().get(url, auth=False)
        return response
