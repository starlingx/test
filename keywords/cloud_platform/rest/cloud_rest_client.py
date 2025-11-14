from config.configuration_manager import ConfigurationManager
from framework.rest.rest_client import RestClient
from framework.rest.rest_response import RestResponse
from framework.rest.ssh_tunnel_rest_client import SSHTunnelRestClient
from keywords.cloud_platform.rest.get_auth_token_keywords import GetAuthTokenKeywords


class CloudRestClient:
    """
    Class for Cloud Rest Client.
    """

    def __init__(self):
        # Use SSH tunnel client if jump host is configured
        config = ConfigurationManager.get_lab_config()
        if config.is_use_jump_server():
            self.rest_client = SSHTunnelRestClient()
        else:
            self.rest_client = RestClient()

        self.auth_token = GetAuthTokenKeywords(self.rest_client).get_token()

    def get(self, url: str) -> RestResponse:
        """
        Runs a get on the url.

        Args:
            url (str): the url for the get request

        Returns:
            RestResponse: The response from the GET request
        """
        headers = {"X-Auth-Token": self.auth_token}
        rest_response = self.rest_client.get(url, headers)
        return rest_response
