from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords
from keywords.cloud_platform.system.host.objects.system_host_memory_output import SystemHostMemoryOutput


class GetHostMemoryKeywords(BaseKeyword):
    """
    Keywords for get host memory from Rest API
    """

    def __init__(self):
        self.bare_metal_base_url = GetRestUrlKeywords().get_bare_metal_url()

    def get_memory(self, host_id: str) -> SystemHostMemoryOutput:
        """
        Get hosts memory using the rest api
        Returns:

        """
        response = CloudRestClient().get(f"{self.bare_metal_base_url}/ihosts/{host_id}/imemorys")
        self.validate_success_status_code(response)
        system_host_memory_output = SystemHostMemoryOutput(response)

        return system_host_memory_output