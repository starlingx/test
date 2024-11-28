
from framework.logging.automation_logger import get_logger
from framework.rest.rest_client import RestClient
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords
from config.configuration_manager import ConfigurationManager


class GetAuthTokenKeywords(BaseKeyword):
    """
    Class for Auth Token Keywords
    """
    def __init__(self) -> None:
        # set the headers
        self.headers = {'Content-type': 'application/json'}

        # Get the rest credentials
        rest_credentials = ConfigurationManager.get_lab_config().get_rest_credentials()

        # reset body needed to get auth token
        self.json_string = (
                '{"auth":'
                '{"identity":{"methods": ["password"],'
                '"password": {"user": {"domain":'
                '{"name": "Default"},"name":'
                f'"{rest_credentials.get_user_name()}","password":"{rest_credentials.get_password()}"'
                '}}},'
                '"scope":{"project": {"name":'
                '"admin","domain": {"name":"Default"}'
                '}}}}'
            )

    def get_token(self):
        """
        Gets the token for a rest api call
        """

        # gets the token
        response = RestClient().post(f"{GetRestUrlKeywords().get_keystone_url()}/auth/tokens", headers=self.headers, data=self.json_string)

        # token is in the header of the response
        headers = response.get_headers()
        token = headers['X-Subject-Token']
        if token:
            return token
        
        get_logger().log_error("unable to find the token")
        return None