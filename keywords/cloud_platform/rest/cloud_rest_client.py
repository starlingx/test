from config.configuration_manager import ConfigurationManager
from framework.rest.rest_client import RestClient
from framework.rest.rest_response import RestResponse
from framework.rest.ssh_tunnel_rest_client import SSHTunnelRestClient
from keywords.cloud_platform.rest.get_auth_token_keywords import GetAuthTokenKeywords


class CloudRestClient:
    """Class for Cloud Rest Client."""

    def __init__(self):
        # Use SSH tunnel client if jump host is configured
        config = ConfigurationManager.get_lab_config()
        if config.is_use_jump_server():
            self.rest_client = SSHTunnelRestClient()
        else:
            self.rest_client = RestClient()

        self.auth_token = GetAuthTokenKeywords(self.rest_client).get_token()

    def get(self, url: str, auth: bool = True) -> RestResponse:
        """Runs a get on the url.

        Args:
            url (str): The url for the get request.
            auth (bool): Whether to include auth token. Defaults to True.

        Returns:
            RestResponse: The response from the GET request.
        """
        headers = {"X-Auth-Token": self.auth_token} if auth else {}
        rest_response = self.rest_client.get(url, headers)
        return rest_response

    def delete(self, url: str, auth: bool = True) -> RestResponse:
        """Runs a delete on the url.

        Args:
            url (str): The url for the delete request.
            auth (bool): Whether to include auth token. Defaults to True.

        Returns:
            RestResponse: The response from the DELETE request.
        """
        headers = {"X-Auth-Token": self.auth_token} if auth else {}
        rest_response = self.rest_client.delete(url, headers)
        return rest_response

    def post(self, url: str, data: dict | str | None = None, auth: bool = True) -> RestResponse:
        """Runs a post on the url.

        Args:
            url (str): The url for the post request.
            data (dict | str | None): The data to send in the body.
            auth (bool): Whether to include auth token. Defaults to True.

        Returns:
            RestResponse: The response from the POST request.
        """
        headers = {"X-Auth-Token": self.auth_token, "Content-Type": "application/json"} if auth else {}
        rest_response = self.rest_client.post(url, data=data or "{}", headers=headers)
        return rest_response

    def patch(self, url: str, data: dict | str | None = None, auth: bool = True) -> RestResponse:
        """Runs a patch on the url.

        Args:
            url (str): The url for the patch request.
            data (dict | str | None): The data to send in the body.
            auth (bool): Whether to include auth token. Defaults to True.

        Returns:
            RestResponse: The response from the PATCH request.
        """
        headers = {"X-Auth-Token": self.auth_token, "Content-Type": "application/json"} if auth else {}
        rest_response = self.rest_client.patch(url, data=data or {}, headers=headers)
        return rest_response

    def put(self, url: str, data: dict | str | None = None, auth: bool = True, content_type: str = "application/json") -> RestResponse:
        """Runs a put on the url.

        Args:
            url (str): The url for the put request.
            data (dict | str | None): The data to send in the body.
            auth (bool): Whether to include auth token. Defaults to True.
            content_type (str): Content-Type header value. Defaults to application/json.

        Returns:
            RestResponse: The response from the PUT request.
        """
        headers = {"X-Auth-Token": self.auth_token, "Content-Type": content_type} if auth else {}
        rest_response = self.rest_client.put(url, data=data or {}, headers=headers)
        return rest_response
