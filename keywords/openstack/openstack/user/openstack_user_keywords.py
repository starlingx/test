from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.openstack.openstack.user.object.openstack_user_list_output import OpenstackUserListOutput


class OpenstackUserListKeywords(BaseKeyword):
    """
    Class for OpenStack User List operations
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the OpenStack controller
        """
        self.ssh_connection = ssh_connection

    def get_openstack_user_list(self) -> OpenstackUserListOutput:
        """
        Get list of all OpenStack users.

        Returns:
            OpenstackUserListOutput: Object containing parsed user list data
        """
        cmd = "openstack user list"
        output = self.ssh_connection.send(source_openrc(cmd), get_pty=True)
        self.validate_success_return_code(self.ssh_connection)

        # Use the complete output, not just the first line
        complete_output = "\n".join(output) if isinstance(output, list) else output

        return OpenstackUserListOutput(complete_output)

    def delete_user(self, user_id: str) -> str:
        """
        Delete an OpenStack user by ID.

        Args:
            user_id (str): The user ID to delete

        Returns:
            str: Command output message
        """
        cmd = f"openstack user delete {user_id}"
        output = self.ssh_connection.send(source_openrc(cmd), get_pty=True)

        # Handle empty output or return complete output
        if not output:
            return "No output received from delete command"

        # Join all output lines to capture complete error message
        return "\n".join(output) if isinstance(output, list) else str(output)
