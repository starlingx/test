"""Output class for host sensorgroup REST API response."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.bare_metal.sensors.objects.host_sensorgroup_object import HostSensorgroupObject


class HostSensorgroupOutput:
    """Parses /ihosts/{id}/isensorgroups REST API response into HostSensorgroupObject list."""

    def __init__(self, response: RestResponse):
        """Initialize HostSensorgroupOutput from REST response.

        Args:
            response (RestResponse): The REST response.
        """
        self.sensorgroup_objects = []
        sensorgroups = response.get_json_content().get("isensorgroups", [])
        for sg in sensorgroups:
            obj = HostSensorgroupObject()
            if sg.get("uuid"):
                obj.set_uuid(sg["uuid"])
            if sg.get("sensorgroupname"):
                obj.set_sensorgroupname(sg["sensorgroupname"])
            if sg.get("status"):
                obj.set_status(sg["status"])
            self.sensorgroup_objects.append(obj)

    def get_sensorgroup_objects(self) -> list[HostSensorgroupObject]:
        """Get list of HostSensorgroupObject.

        Returns:
            list[HostSensorgroupObject]: List of sensorgroup objects.
        """
        return self.sensorgroup_objects
