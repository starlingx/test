from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords
from keywords.cloud_platform.system.host.objects.system_host_if_output import SystemHostInterfaceOutput


class GetInterfacesKeywords(BaseKeyword):
    """
    Keywords for get interfaces
    """

    def __init__(self):
        self.configuration_base_url = GetRestUrlKeywords().get_configuration_url()

    def get_interfaces(self, host_uuid: str) -> SystemHostInterfaceOutput:
        """
        Get interfaces using the rest api

        Args:
            host_uuid(): the uuid of the host to get the interfaces for 
        Returns: list of hosts cpus

        """
        response = CloudRestClient().get(f"{self.configuration_base_url}/ihosts/{host_uuid}/iinterfaces")
        self.validate_success_status_code(response)
        interface_output = SystemHostInterfaceOutput(response)
        
        return interface_output
    