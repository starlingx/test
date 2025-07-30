from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.openstack.command_wrappers import source_admin_openrc
from keywords.openstack.openstack.stack.object.openstack_stack_delete_input import OpenstackStackDeleteInput


class OpenstackStackDeleteKeywords(BaseKeyword):
    """Class for Openstack stack delete keywords"""

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor for OpenstackStackDeleteKeywords class

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller
        """
        self.ssh_connection = ssh_connection

    def get_openstack_stack_delete(self, openstack_stack_delete_input: OpenstackStackDeleteInput) -> str:
        """
        Delete a stack specified in the parameter 'openstack_stack_delete_input'.

        Args:
            openstack_stack_delete_input (OpenstackStackDeleteInput): defines the stack name

        Returns:
            str: a string message indicating the result of the deletion. Examples:
                'Stack hello-kitty deleted.\n'
                'Stack-delete rejected: stack not found.\n'
        """
        cmd = self.get_command(openstack_stack_delete_input)
        output = self.ssh_connection.send(source_admin_openrc(cmd), get_pty=True)
        self.validate_success_return_code(self.ssh_connection)

        return output[0]

    def get_command(self, openstack_stack_delete_input: OpenstackStackDeleteInput) -> str:
        """
        Generates the 'openstack stack delete' command using values from the given input object.

        Args:
            openstack_stack_delete_input (OpenstackStackDeleteInput): Input parameters for the delete command

        Returns:
            str: a string representing the 'openstack stack delete' command, configured according to the parameters in the 'openstack_stack_delete_input' argument.
        """
        cmd = f"openstack stack delete -y {openstack_stack_delete_input.get_stack_name()}"
        return cmd
