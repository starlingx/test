from typing import Any, Dict, Optional

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.rest.rest_client import RestClient
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class GetAuthTokenKeywords(BaseKeyword):
    """
    Keywords for obtaining authentication tokens from Keystone API.

    This class handles the authentication process with OpenStack Keystone
    to retrieve X-Auth-Token for subsequent API calls.
    """

    def __init__(self, rest_client: RestClient) -> None:
        """
        Initialize the authentication token keywords.

        Args:
            rest_client (RestClient): REST client instance for making HTTP requests
        """
        self.headers: Dict[str, str] = {"Content-type": "application/json"}
        self.rest_client: RestClient = rest_client

        # Get the rest credentials
        rest_credentials = ConfigurationManager.get_lab_config().get_rest_credentials()

        # JSON body needed to get auth token
        self.json_string: str = '{"auth":' '{"identity":{"methods": ["password"],' '"password": {"user": {"domain":' '{"name": "Default"},"name":' f'"{rest_credentials.get_user_name()}","password":"{rest_credentials.get_password()}"' "}}}," '"scope":{"project": {"name":' '"admin","domain": {"name":"Default"}' "}}}}"

    def get_token(self) -> Optional[str]:
        """
        Retrieve authentication token from Keystone API.

        Makes a POST request to the Keystone /auth/tokens endpoint with
        admin credentials to obtain an X-Subject-Token for API authentication.

        Returns:
            Optional[str]: Authentication token string if successful, None if failed

        Raises:
            None: May log errors but does not raise exceptions
        """
        # Get the token from Keystone
        response = self.rest_client.post(f"{GetRestUrlKeywords().get_keystone_url()}/auth/tokens", headers=self.headers, data=self.json_string)

        # Check if authentication was successful
        if response.get_status_code() != 201:
            get_logger().log_error(f"Authentication failed with status {response.get_status_code()}: {response.response.text}")
            return None

        # Token is in the response headers
        headers: Dict[str, Any] = response.get_headers()
        if "X-Subject-Token" in headers:
            return headers["X-Subject-Token"]

        get_logger().log_error("Unable to find X-Subject-Token in response headers")
        return None
