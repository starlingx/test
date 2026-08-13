"""Output class for ServicenodeOutput."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.configuration.servicenodes.objects.servicenode_object import ServicenodeObject


class ServicenodeOutput:
    """Parses /servicenodes REST API response into ServicenodeObject list."""

    def __init__(self, response: RestResponse):
        """Initialize ServicenodeOutput from REST response.

        Args:
            response (RestResponse): The REST response.
        """
        self.objects = []
        items = response.get_json_content().get("inodes", [])
        for item in items:
            obj = ServicenodeObject()
            if item.get("uuid"):
                obj.set_uuid(item["uuid"])
            if item.get("name"):
                obj.set_name(item["name"])
            if item.get("operational_state"):
                obj.set_operational_state(item["operational_state"])
            self.objects.append(obj)

    def get_servicenodeobjects(self) -> list[ServicenodeObject]:
        """Get list of ServicenodeObject.

        Returns:
            list[ServicenodeObject]: List of ServicenodeObject instances.
        """
        return self.objects
