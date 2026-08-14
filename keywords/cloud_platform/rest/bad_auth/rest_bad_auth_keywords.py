"""Keywords for testing unauthenticated REST API access."""

from framework.rest.rest_response import RestResponse
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class RestBadAuthKeywords(BaseKeyword):
    """Keywords for testing unauthenticated access to REST API endpoints."""

    def __init__(self):
        """Initialize RestBadAuthKeywords with configuration URL."""
        self.base_url = GetRestUrlKeywords().get_configuration_url()

    def get_without_auth(self, resource: str) -> RestResponse:
        """GET a resource without authentication.

        Args:
            resource (str): The API resource path (e.g., '/addrpools').

        Returns:
            RestResponse: The raw response for status validation.
        """
        response = CloudRestClient().get(f"{self.base_url}{resource}", auth=False)
        return response

    def delete_without_auth(self, resource: str) -> RestResponse:
        """DELETE a resource without authentication.

        Args:
            resource (str): The API resource path.

        Returns:
            RestResponse: The raw response for status validation.
        """
        response = CloudRestClient().delete(f"{self.base_url}{resource}", auth=False)
        return response

    def patch_without_auth(self, resource: str) -> RestResponse:
        """PATCH a resource without authentication.

        Args:
            resource (str): The API resource path.

        Returns:
            RestResponse: The raw response for status validation.
        """
        response = CloudRestClient().patch(f"{self.base_url}{resource}", data={}, auth=False)
        return response

    def post_without_auth(self, resource: str) -> RestResponse:
        """POST a resource without authentication.

        Args:
            resource (str): The API resource path.

        Returns:
            RestResponse: The raw response for status validation.
        """
        response = CloudRestClient().post(f"{self.base_url}{resource}", data="{}", auth=False)
        return response

    def put_without_auth(self, resource: str) -> RestResponse:
        """PUT a resource without authentication.

        Args:
            resource (str): The API resource path.

        Returns:
            RestResponse: The raw response for status validation.
        """
        response = CloudRestClient().put(f"{self.base_url}{resource}", data={}, auth=False)
        return response
