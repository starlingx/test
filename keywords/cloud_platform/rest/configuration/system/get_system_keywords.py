from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.configuration.system.objects.system_output import SystemOutput
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class GetSystemKeywords(BaseKeyword):

    def __init__(self):
        self.configuration_base_url = GetRestUrlKeywords().get_configuration_url()

    def get_system(self):
        """
        Get system using the rest api
        Returns: list of hosts

        """
        response = CloudRestClient().get(f"{self.configuration_base_url}/isystems")
        self.validate_success_status_code(response)
        system_output = SystemOutput(response)
        return system_output