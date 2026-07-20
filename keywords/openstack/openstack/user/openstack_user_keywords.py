import shlex

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

    def create_user(self, username: str, password: str) -> str:
        """
        Create an OpenStack user.

        Args:
            username (str): The username for the new user.
            password (str): The password for the new user.

        Returns:
            str: Command output from user creation.
        """
        cmd = f"openstack user create {username} --password {shlex.quote(password)}"
        output = self.ssh_connection.send(source_openrc(cmd), get_pty=True)
        self.validate_success_return_code(self.ssh_connection)

        return "\n".join(output) if isinstance(output, list) else output

    def show_user(self, username: str) -> str:
        """
        Show details of an OpenStack user.

        Args:
            username (str): The username or ID to show.

        Returns:
            str: Command output from user show.
        """
        cmd = f"openstack user show {username}"
        output = self.ssh_connection.send(source_openrc(cmd), get_pty=True)
        self.validate_success_return_code(self.ssh_connection)

        return "\n".join(output) if isinstance(output, list) else output

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
