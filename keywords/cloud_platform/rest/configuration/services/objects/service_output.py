"""Output class for ServiceOutput."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.configuration.services.objects.service_object import ServiceObject


class ServiceOutput:
    """Parses /services REST API response into ServiceObject list."""

    def __init__(self, response: RestResponse):
        """Initialize ServiceOutput from REST response.

        Args:
            response (RestResponse): The REST response.
        """
        self.objects = []
        items = response.get_json_content().get("services", [])
        for item in items:
            obj = ServiceObject()
            if item.get("uuid"):
                obj.set_uuid(item["uuid"])
            if item.get("servicename"):
                obj.set_servicename(item["servicename"])
            if item.get("state"):
                obj.set_state(item["state"])
            self.objects.append(obj)

    def get_serviceobjects(self) -> list[ServiceObject]:
        """Get list of ServiceObject.

        Returns:
            list[ServiceObject]: List of ServiceObject instances.
        """
        return self.objects
