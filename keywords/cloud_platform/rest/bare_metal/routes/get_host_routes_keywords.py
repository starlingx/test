"""Keywords for retrieving host route information via REST API."""

from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.bare_metal.routes.objects.host_route_output import HostRouteOutput
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class GetHostRoutesKeywords(BaseKeyword):
    """Keywords for retrieving host route information via REST API."""

    def __init__(self):
        """Initialize GetHostRoutesKeywords with configuration URL."""
        self.configuration_base_url = GetRestUrlKeywords().get_configuration_url()

    def get_host_routes(self, host_id: str) -> HostRouteOutput:
        """Get host routes using the REST API.

        Args:
            host_id (str): The UUID of the host.

        Returns:
            HostRouteOutput: Parsed route output with HostRouteObject list.
        """
        response = CloudRestClient().get(f"{self.configuration_base_url}/ihosts/{host_id}/routes")
        self.validate_success_status_code(response)
        return HostRouteOutput(response)
