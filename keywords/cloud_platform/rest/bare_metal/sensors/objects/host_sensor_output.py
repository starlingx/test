"""Output class for host sensor REST API response."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.bare_metal.sensors.objects.host_sensor_object import HostSensorObject


class HostSensorOutput:
    """Parses /ihosts/{id}/isensors REST API response into HostSensorObject list."""

    def __init__(self, response: RestResponse):
        """Initialize HostSensorOutput from REST response.

        Args:
            response (RestResponse): The REST response.
        """
        self.sensor_objects = []
        sensors = response.get_json_content().get("isensors", [])
        for sensor in sensors:
            obj = HostSensorObject()
            if sensor.get("uuid"):
                obj.set_uuid(sensor["uuid"])
            if sensor.get("sensorname"):
                obj.set_sensorname(sensor["sensorname"])
            if sensor.get("status"):
                obj.set_status(sensor["status"])
            self.sensor_objects.append(obj)

    def get_sensor_objects(self) -> list[HostSensorObject]:
        """Get list of HostSensorObject.

        Returns:
            list[HostSensorObject]: List of sensor objects.
        """
        return self.sensor_objects
