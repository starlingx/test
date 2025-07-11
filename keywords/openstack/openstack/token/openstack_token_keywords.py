from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.openstack.openstack.token.object.openstack_token_issue_output import OpenstackTokenIssueOutput


class OpenstackTokenKeywords(BaseKeyword):
    """
    Class for OpenStack Token operations
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the OpenStack controller
        """
        self.ssh_connection = ssh_connection

    def token_issue(self) -> OpenstackTokenIssueOutput:
        """
        Issue an OpenStack authentication token.

        Returns:
            OpenstackTokenIssueOutput: Object containing parsed token data
        """
        cmd = "openstack token issue"
        output = self.ssh_connection.send(source_openrc(cmd), get_pty=True)
        self.validate_success_return_code(self.ssh_connection)

        complete_output = "\n".join(output) if isinstance(output, list) else output
        return OpenstackTokenIssueOutput(complete_output)

    def get_auth_token(self) -> str:
        """
        Get authentication token ID for API calls.

        Returns:
            str: Authentication token ID
        """
        token_output = self.token_issue()
        return token_output.get_token_id()
