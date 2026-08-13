"""Output class for NetworkOutput."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.configuration.networks.objects.network_object import NetworkObject


class NetworkOutput:
    """Parses /networks REST API response into NetworkObject list."""

    def __init__(self, response: RestResponse):
        """Initialize NetworkOutput from REST response.

        Args:
            response (RestResponse): The REST response.
        """
        self.objects = []
        items = response.get_json_content().get("networks", [])
        for item in items:
            obj = NetworkObject()
            if item.get("uuid"):
                obj.set_uuid(item["uuid"])
            if item.get("name"):
                obj.set_name(item["name"])
            if item.get("type"):
                obj.set_type(item["type"])
            self.objects.append(obj)

    def get_networkobjects(self) -> list[NetworkObject]:
        """Get list of NetworkObject.

        Returns:
            list[NetworkObject]: List of NetworkObject instances.
        """
        return self.objects
