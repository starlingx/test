from framework.rest.rest_client import RestClient
from keywords.cloud_platform.rest.get_auth_token_keywords import GetAuthTokenKeywords


class CloudRestClient:
    """
    Class for Cloud Rest Client.
    """
    def __init__(self):
        self.auth_token = GetAuthTokenKeywords().get_token()

    def get(self, url: str):
        """
        Runs a get on the url
        Args:
            url: the url for the get request        

        Returns: the response
        """
        headers = {'X-Auth-Token': self.auth_token}
        rest_response = RestClient().get(url, headers)
        return rest_response
    



