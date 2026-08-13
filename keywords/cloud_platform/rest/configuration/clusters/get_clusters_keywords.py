"""Keywords for GetClustersKeywords."""

from framework.rest.rest_response import RestResponse
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.configuration.clusters.objects.cluster_output import ClusterOutput
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class GetClustersKeywords(BaseKeyword):
    """Keywords for /clusters REST API operations."""

    def __init__(self):
        """Initialize GetClustersKeywords with configuration URL."""
        self.base_url = GetRestUrlKeywords().get_configuration_url()

    def get_clusters(self) -> ClusterOutput:
        """Get clusters from REST API.

        Returns:
            ClusterOutput: Parsed output.
        """
        response = CloudRestClient().get(f"{self.base_url}/clusters")
        self.validate_success_status_code(response)
        return ClusterOutput(response)

    def get_clusters_with_error(self, resource_id: str = "") -> RestResponse:
        """Get /clusters with invalid ID expecting error.

        Args:
            resource_id (str): The resource ID (may be invalid).

        Returns:
            RestResponse: The raw response for error validation.
        """
        url = f"{self.base_url}/clusters/{resource_id}" if resource_id else f"{self.base_url}/clusters"
        response = CloudRestClient().get(url)
        return response

    def get_clusters_no_auth(self, resource_id: str = "") -> RestResponse:
        """Get /clusters without authentication.

        Args:
            resource_id (str): The resource ID.

        Returns:
            RestResponse: The raw response for auth validation.
        """
        url = f"{self.base_url}/clusters/{resource_id}" if resource_id else f"{self.base_url}/clusters"
        response = CloudRestClient().get(url, auth=False)
        return response
