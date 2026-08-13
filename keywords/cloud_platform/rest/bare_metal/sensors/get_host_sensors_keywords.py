"""Keywords for retrieving host sensor information via REST API."""

from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.bare_metal.sensors.objects.host_sensor_output import HostSensorOutput
from keywords.cloud_platform.rest.bare_metal.sensors.objects.host_sensorgroup_output import HostSensorgroupOutput
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class GetHostSensorsKeywords(BaseKeyword):
    """Keywords for retrieving host sensor and sensorgroup information via REST API."""

    def __init__(self):
        """Initialize GetHostSensorsKeywords with configuration URL."""
        self.configuration_base_url = GetRestUrlKeywords().get_configuration_url()

    def get_host_sensors(self, host_id: str) -> HostSensorOutput:
        """Get host sensors using the REST API.

        Args:
            host_id (str): The UUID of the host.

        Returns:
            HostSensorOutput: Parsed sensor output with HostSensorObject list.
        """
        response = CloudRestClient().get(f"{self.configuration_base_url}/ihosts/{host_id}/isensors")
        self.validate_success_status_code(response)
        return HostSensorOutput(response)

    def get_host_sensorgroups(self, host_id: str) -> HostSensorgroupOutput:
        """Get host sensor groups using the REST API.

        Args:
            host_id (str): The UUID of the host.

        Returns:
            HostSensorgroupOutput: Parsed sensorgroup output.
        """
        response = CloudRestClient().get(f"{self.configuration_base_url}/ihosts/{host_id}/isensorgroups")
        self.validate_success_status_code(response)
        return HostSensorgroupOutput(response)
