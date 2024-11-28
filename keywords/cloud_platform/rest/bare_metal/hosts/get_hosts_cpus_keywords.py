from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords
from keywords.cloud_platform.system.host.objects.system_host_cpu_output import SystemHostCPUOutput


class GetHostsCpusKeywords(BaseKeyword):
    """
    Keywords for getting Host Cpus from Rest API
    """

    def __init__(self):
        self.bare_metal_base_url = GetRestUrlKeywords().get_bare_metal_url()

    def get_hosts_cpus(self, uuid: str) -> SystemHostCPUOutput:
        """
        Get hosts cpus using the rest api
        Returns: list of hosts cpus

        """
        response = CloudRestClient().get(f"{self.bare_metal_base_url}/ihosts/{uuid}/icpus")
        self.validate_success_status_code(response)
        system_host_cpu_output = SystemHostCPUOutput(response)
        return system_host_cpu_output
    