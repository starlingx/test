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

    def post_nested_resources(self, resource_pool_id: str) -> O2RestResponse:
        """POST to the read-only resources sub-collection nested under a resource pool.

        The pool id is never dereferenced: the rejection happens while the request is
        being routed, from the path shape and the method alone, before the resource
        class is dispatched and before any pool lookup. A generated id is therefore as
        valid as a real one and removes a dependency on lab inventory state.

        Args:
            resource_pool_id (str): The resource pool id to nest the path under.

        Returns:
            O2RestResponse: The raw response for the caller to assert the status.
        """
        return self.o2_rest_client.post(self.url_keywords.get_local_inventory_endpoint_url(f"v1/resourcePools/{resource_pool_id}/resources"), data="{}")

    def post_deployment_managers(self) -> O2RestResponse:
        """POST to the read-only deploymentManagers collection.

        Returns:
            O2RestResponse: The raw response for the caller to assert the status.
        """
        return self.o2_rest_client.post(self.url_keywords.get_local_inventory_endpoint_url("v1/deploymentManagers"), data="{}")

    def post_version_root(self) -> O2RestResponse:
        """POST to the read-only inventory version root.

        Returns:
            O2RestResponse: The raw response for the caller to assert the status.
        """
        return self.o2_rest_client.post(self.url_keywords.get_local_inventory_endpoint_url("v1/"), data="{}")

    def patch_subscriptions(self) -> O2RestResponse:
        """PATCH the inventory subscriptions collection, which supports no such method.

        Returns:
            O2RestResponse: The raw response for the caller to assert the status.
        """
        return self.o2_rest_client.patch(self.url_keywords.get_local_inventory_endpoint_url("v1/subscriptions"), data="{}")

    def post_alarms(self) -> O2RestResponse:
        """POST to the read-only monitoring alarms collection.

        Returns:
            O2RestResponse: The raw response for the caller to assert the status.
        """
        return self.o2_rest_client.post(self.url_keywords.get_local_monitoring_endpoint_url("v1/alarms"), data="{}")

    def patch_alarm_subscriptions(self) -> O2RestResponse:
        """PATCH the monitoring alarmSubscriptions collection, which supports no such method.

        Returns:
            O2RestResponse: The raw response for the caller to assert the status.
        """
        return self.o2_rest_client.patch(self.url_keywords.get_local_monitoring_endpoint_url("v1/alarmSubscriptions"), data="{}")

    def patch_alarm(self, alarm_id: str) -> O2RestResponse:
        """PATCH an alarm event record by id, to clear it.

        Args:
            alarm_id (str): The alarm event record id to PATCH.

        Returns:
            O2RestResponse: The raw response for the caller to assert the status.
        """
        # Three properties of this body each decide which status comes back, so none
        # of them is incidental:
        #   - The severity is a quoted JSON string. The severity enum carries a str
        #     mixin, so its cleared member coerces to '5'; a JSON integer is rejected
        #     as invalid with 400, which would mask the status under test.
        #   - Exactly one of the two mutually exclusive fields is sent. The handler
        #     checks exclusivity before existence, so sending both or neither returns
        #     400 and never reaches the not-found path.
        #   - The clear field is used rather than the acknowledge field. A falsy
        #     acknowledge value skips its branch and falls through to the same 404, so
        #     an acknowledge-shaped body would pass while proving nothing.
        return self.o2_rest_client.patch(self.url_keywords.get_local_monitoring_endpoint_url(f"v1/alarms/{alarm_id}"), data='{"perceivedSeverity": "5"}')
