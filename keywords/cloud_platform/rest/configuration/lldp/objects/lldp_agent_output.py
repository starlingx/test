"""Output class for LLDP Agent."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.configuration.lldp.objects.lldp_object import LldpObject


class LldpAgentOutput:
    """Parses /lldp_agents REST API response."""

    def __init__(self, response: RestResponse):
        """Initialize LldpAgentOutput.

        Args:
            response (RestResponse): The REST response.
        """
        self.objects = []
        items = response.get_json_content().get("lldp_agents", [])
        for item in items:
            obj = LldpObject()
            if item.get("uuid"):
                obj.set_uuid(item["uuid"])
            if item.get("port_identifier"):
                obj.set_port_identifier(item["port_identifier"])
            if item.get("chassis_id"):
                obj.set_chassis_id(item["chassis_id"])
            self.objects.append(obj)

    def get_lldp_agent_objects(self) -> list[LldpObject]:
        """Get list of LldpObject.

        Returns:
            list[LldpObject]: List of LLDP agent objects.
        """
        return self.objects
