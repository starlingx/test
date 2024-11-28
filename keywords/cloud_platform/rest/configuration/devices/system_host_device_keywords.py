from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords
from keywords.cloud_platform.system.host.objects.system_host_device_output import SystemHostDeviceOutput


class GetHostDevicesKeywords(BaseKeyword):
    """
    Keywords for get Host Devices
    """

    def __init__(self):
        self.configuration_base_url = GetRestUrlKeywords().get_configuration_url()

    def get_devices(self, host_uuid: str) -> SystemHostDeviceOutput:
        """
        Get host devices using the rest api

        Args:
            host_uuid(): the uuid of the host to get the devices for 
        Returns: list of hosts cpus

        """
        response = CloudRestClient().get(f"{self.configuration_base_url}/ihosts/{host_uuid}/pci_devices")
        self.validate_success_status_code(response)
        system_host_device_output = SystemHostDeviceOutput(response)

        return system_host_device_output
        