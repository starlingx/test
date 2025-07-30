from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.openstack.command_wrappers import source_admin_openrc
from keywords.openstack.openstack.stack.object.openstack_stack_list_output import OpenstackStackListOutput


class OpenstackStackListKeywords(BaseKeyword):
    """Class for Openstack stack list keywords"""

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor for OpenstackStackListKeywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller
        """
        self.ssh_connection = ssh_connection

    def get_openstack_stack_list(self) -> OpenstackStackListOutput:
        """
        Gets a OpenstackStackListOutput object related to the execution of the 'openstack stack list' command.

        Returns:
             OpenstackStackListOutput: an instance of the OpenstackStackListOutput object representing the
             heat stacks on the host, as a result of the execution of the 'openstack stack list' command.
        """
        output = self.ssh_connection.send(source_admin_openrc("openstack stack list -f json"), get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        openstack_stack_list_output = OpenstackStackListOutput(output)

        return openstack_stack_list_output

    def validate_stack_status(self, stack_name: str, status: str) -> None:
        """
        This function will validate that the stack specified reaches the desired status.

        Args:
            stack_name (str): Name of the stack that we are waiting for.
            status (str): Status in which we want to wait for the stack to reach.
        """

        def get_stack_status():
            openstack_stacks = self.get_openstack_stack_list()
            stack_status = openstack_stacks.get_stack(stack_name).get_stack_status()
            return stack_status

        message = f"Openstack stack {stack_name}'s status is {status}"
        validate_equals_with_retry(get_stack_status, status, message, timeout=300)
