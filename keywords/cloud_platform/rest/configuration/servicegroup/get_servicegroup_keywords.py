"""Keywords for GetServicegroupKeywords."""

from framework.rest.rest_response import RestResponse
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.configuration.servicegroup.objects.servicegroup_output import ServicegroupOutput
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class GetServicegroupKeywords(BaseKeyword):
    """Keywords for /servicegroup REST API operations."""

    def __init__(self):
        """Initialize GetServicegroupKeywords with configuration URL."""
        self.base_url = GetRestUrlKeywords().get_configuration_url()

    def get_sm_servicegroup(self) -> ServicegroupOutput:
        """Get sm_servicegroup from REST API.

        Returns:
            ServicegroupOutput: Parsed output.
        """
        response = CloudRestClient().get(f"{self.base_url}/servicegroup")
        self.validate_success_status_code(response)
        return ServicegroupOutput(response)

    def get_sm_servicegroup_with_error(self, resource_id: str = "") -> RestResponse:
        """Get /servicegroup with invalid ID expecting error.

        Args:
            resource_id (str): The resource ID (may be invalid).

        Returns:
            RestResponse: The raw response for error validation.
        """
        url = f"{self.base_url}/servicegroup/{resource_id}" if resource_id else f"{self.base_url}/servicegroup"
        response = CloudRestClient().get(url)
        return response

    def get_sm_servicegroup_no_auth(self, resource_id: str = "") -> RestResponse:
        """Get /servicegroup without authentication.

        Args:
            resource_id (str): The resource ID.

        Returns:
            RestResponse: The raw response for auth validation.
        """
        url = f"{self.base_url}/servicegroup/{resource_id}" if resource_id else f"{self.base_url}/servicegroup"
        response = CloudRestClient().get(url, auth=False)
        return response
