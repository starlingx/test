"""Output class for ServicegroupOutput."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.configuration.servicegroup.objects.servicegroup_object import ServicegroupObject


class ServicegroupOutput:
    """Parses /servicegroup REST API response into ServicegroupObject list."""

    def __init__(self, response: RestResponse):
        """Initialize ServicegroupOutput from REST response.

        Args:
            response (RestResponse): The REST response.
        """
        self.objects = []
        items = response.get_json_content().get("sm_servicegroup", [])
        for item in items:
            obj = ServicegroupObject()
            if item.get("uuid"):
                obj.set_uuid(item["uuid"])
            if item.get("service_group_name"):
                obj.set_service_group_name(item["service_group_name"])
            if item.get("state"):
                obj.set_state(item["state"])
            self.objects.append(obj)

    def get_servicegroupobjects(self) -> list[ServicegroupObject]:
        """Get list of ServicegroupObject.

        Returns:
            list[ServicegroupObject]: List of ServicegroupObject instances.
        """
        return self.objects
