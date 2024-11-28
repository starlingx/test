from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords
from keywords.cloud_platform.system.host.objects.system_host_port_output import SystemHostPortOutput


class GetHostPortsKeywords(BaseKeyword):
    """
    Keywords for get host ports from Rest API
    """

    def __init__(self):
        self.bare_metal_base_url = GetRestUrlKeywords().get_bare_metal_url()

    def get_ports(self, host_id: str) -> SystemHostPortOutput:
        """
        Get hosts ports using the rest api
        Returns: list of ports

        """
        response = CloudRestClient().get(f"{self.bare_metal_base_url}/ihosts/{host_id}/ports")
        self.validate_success_status_code(response)
        system_host_port_output = SystemHostPortOutput(response)

        return system_host_port_output
    
        