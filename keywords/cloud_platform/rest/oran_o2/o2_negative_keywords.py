from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.oran_o2.o2_rest_client import O2RestClient
from keywords.cloud_platform.rest.oran_o2.o2_url_keywords import GetO2UrlKeywords
from keywords.cloud_platform.rest.oran_o2.object.o2_rest_response import O2RestResponse

# A syntactically valid but nonexistent subscription id, so the DELETE 404 test
# creates and destroys nothing.
NONEXISTENT_SUBSCRIPTION_ID = "69253c4b-8398-4602-855d-783865f5f25c"


class O2NegativeKeywords(BaseKeyword):
    """Keywords for O2 IMS API negative-path checks.

    Each method issues a single request through the O2 client and returns the raw
    response so the test asserts the exact status. No retry or refresh is
    introduced: the public client observes the raw server status.
    """

    def __init__(self, o2_rest_client: O2RestClient):
        """Constructor.

        Args:
            o2_rest_client (O2RestClient): Client that executes the requests on the
                controller with the client certificate.
        """
        self.o2_rest_client = o2_rest_client
        self.url_keywords = GetO2UrlKeywords()

    def get_ocloud_root_no_auth(self) -> O2RestResponse:
        """GET the O-Cloud root with the client cert but no Authorization header.

        Returns:
            O2RestResponse: The raw response for the caller to assert the status.
        """
        return self.o2_rest_client.get_no_auth(self.url_keywords.get_local_inventory_endpoint_url("v1/"))

    def get_ocloud_root_invalid_token(self, token: str) -> O2RestResponse:
        """GET the O-Cloud root (a param-free endpoint) with a malformed Bearer token.

        Args:
            token (str): The malformed Bearer token to present.

        Returns:
            O2RestResponse: The raw response for the caller to assert the status.
        """
        return self.o2_rest_client.get_with_token(self.url_keywords.get_local_inventory_endpoint_url("v1/"), token)

    def post_resource_pools(self) -> O2RestResponse:
        """POST to the read-only resourcePools collection.

        Returns:
            O2RestResponse: The raw response for the caller to assert the status.
        """
        return self.o2_rest_client.post(self.url_keywords.get_local_inventory_endpoint_url("v1/resourcePools"), data="{}")

    def delete_subscription(self, subscription_id: str) -> O2RestResponse:
        """DELETE a subscription by id.

        Args:
            subscription_id (str): The subscription id to delete.

        Returns:
            O2RestResponse: The raw response for the caller to assert the status.
        """
        return self.o2_rest_client.delete(self.url_keywords.get_local_inventory_endpoint_url(f"v1/subscriptions/{subscription_id}"))
