from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.openstack.openstack.token.openstack_token_keywords import OpenstackTokenKeywords


class OpenstackUserCurlKeywords(BaseKeyword):
    """
    Class for OpenStack User operations using curl commands
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the OpenStack controller
        """
        self.ssh_connection = ssh_connection

    def get_auth_token(self) -> str:
        """
        Get authentication token for API calls.

        Returns:
            str: Authentication token

        Raises:
            KeywordException: If token cannot be retrieved
        """
        token_keywords = OpenstackTokenKeywords(self.ssh_connection)
        token = token_keywords.get_auth_token()
        if not token:
            raise KeywordException("Failed to retrieve authentication token")
        return token

    def get_lab_fip(self) -> str:
        """
        Get the floating IP for the lab environment.

        Uses the ACE framework configuration manager.

        Returns:
            str: Floating IP address with brackets for IPv6, without for IPv4
        """
        lab_config = ConfigurationManager.get_lab_config()
        fip = lab_config.get_floating_ip()

        if lab_config.is_ipv6():
            return f"[{fip}]"
        return fip

    def delete_user_via_curl(self, user_id: str) -> tuple:
        """
        Delete user via curl command.

        Args:
            user_id (str): User ID to delete

        Returns:
            tuple: (return_code, output)
        """
        token = self.get_auth_token()
        fip = self.get_lab_fip()

        curl_cmd = f'curl -s -X DELETE "https://{fip}:5000/v3/users/{user_id}" -H "X-Auth-Token: {token}" | python -m json.tool'

        output = self.ssh_connection.send(curl_cmd, get_pty=True)
        return_code = self.ssh_connection.get_return_code()
        return return_code, "\n".join(output) if isinstance(output, list) else output
