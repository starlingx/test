from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords
from keywords.cloud_platform.system.host.objects.system_host_stor_output import SystemHostStorageOutput


class GetStorageKeywords(BaseKeyword):
    """
    Keywords for get interfaces
    """

    def __init__(self):
        self.configuration_base_url = GetRestUrlKeywords().get_configuration_url()

    def get_storage(self, host_uuid: str) -> SystemHostStorageOutput:
        """
        Get interfaces using the rest api

        Args:
            host_uuid(): the uuid of the host to get the interfaces for 
        Returns: list of hosts cpus

        """
        response = CloudRestClient().get(f"{self.configuration_base_url}/ihosts/{host_uuid}/istors")
        self.validate_success_status_code(response)
        storage_output = SystemHostStorageOutput(response)
        
        return storage_output