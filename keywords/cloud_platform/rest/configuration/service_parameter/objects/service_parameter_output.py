"""Output class for ServiceParameterOutput."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.configuration.service_parameter.objects.service_parameter_object import ServiceParameterObject


class ServiceParameterOutput:
    """Parses /service_parameter REST API response into ServiceParameterObject list."""

    def __init__(self, response: RestResponse):
        """Initialize ServiceParameterOutput from REST response.

        Args:
            response (RestResponse): The REST response.
        """
        self.objects = []
        items = response.get_json_content().get("parameters", [])
        for item in items:
            obj = ServiceParameterObject()
            if item.get("uuid"):
                obj.set_uuid(item["uuid"])
            if item.get("service"):
                obj.set_service(item["service"])
            if item.get("section"):
                obj.set_section(item["section"])
            if item.get("name"):
                obj.set_name(item["name"])
            if item.get("value"):
                obj.set_value(item["value"])
            self.objects.append(obj)

    def get_serviceparameterobjects(self) -> list[ServiceParameterObject]:
        """Get list of ServiceParameterObject.

        Returns:
            list[ServiceParameterObject]: List of ServiceParameterObject instances.
        """
        return self.objects
