from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords
from keywords.cloud_platform.system.host.objects.system_host_show_output import SystemHostShowOutput


class GetHostsKeywords(BaseKeyword):

    def __init__(self):
        self.bare_metal_base_url = GetRestUrlKeywords().get_bare_metal_url()

    def get_hosts(self):
        """
        Get hosts using the rest api
        Returns: list of hosts

        """
        response = CloudRestClient().get(f"{self.bare_metal_base_url}/ihosts")
        self.validate_success_status_code(response)
        system_host_show_output = SystemHostShowOutput(response)
        return system_host_show_output
    
    def get_host(self, host_id):
        """
        Get hosts using the rest api
        Args:
            host_id (): the id of the host as appears in System Host Show
        Returns: list of hosts

        """
        response = CloudRestClient().get(f"{self.bare_metal_base_url}/ihosts/{host_id}")
        self.validate_success_status_code(response)
        system_host_show_output = SystemHostShowOutput(response)
        return system_host_show_output