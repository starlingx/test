from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.openstack.command_wrappers import source_admin_openrc
from keywords.openstack.openstack.stack.object.openstack_stack_output import OpenstackStackOutput
from keywords.openstack.openstack.stack.object.openstack_stack_status_enum import OpenstackStackStatusEnum
from keywords.openstack.openstack.stack.object.openstack_stack_update_input import OpenstackStackUpdateInput
from keywords.openstack.openstack.stack.openstack_stack_list_keywords import OpenstackStackListKeywords
from keywords.python.string import String


class OpenstackStackUpdateKeywords(BaseKeyword):
    """Class for Openstack Stack Update Keywords"""

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor for OpenstackStackUpdateKeywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller
        """
        self.ssh_connection = ssh_connection

    def openstack_stack_update(self, openstack_stack_update_input: OpenstackStackUpdateInput) -> OpenstackStackOutput:
        """
        Openstack stack update function, updates a given existing stack

        Args:
            openstack_stack_update_input (OpenstackStackUpdateInput): an object with the required parameters

        Returns:
            OpenstackStackOutput: the output of the openstack stack update command
        """
        # Gets the command 'openstack stack update' with its parameters configured.
        cmd = self.get_command(openstack_stack_update_input)
        stack_name = openstack_stack_update_input.get_stack_name()

        # Executes the command 'openstack stack update'.
        output = self.ssh_connection.send(source_admin_openrc(cmd), get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        openstack_stack_output = OpenstackStackOutput(output)

        # Tracks the execution of the command 'openstack stack update' until its completion or a timeout.
        openstack_stack_list_keywords = OpenstackStackListKeywords(self.ssh_connection)
        openstack_stack_list_keywords.validate_stack_status(stack_name, "UPDATE_COMPLETE")

        # If the execution arrived here the status of the stack is 'updated'.
        openstack_stack_output.get_openstack_stack_object().set_stack_status("update_complete")

        return openstack_stack_output

    def is_already_updated(self, stack_name: str) -> bool:
        """
        Verifies if the stack has already been updated.

        Args:
            stack_name (str): a string representing the name of the stack.

        Returns:
            bool: True if the stack named 'stack_name' has already been updated; False otherwise.
        """
        openstack_stack_list_keywords = OpenstackStackListKeywords(self.ssh_connection)
        if openstack_stack_list_keywords.get_openstack_stack_list().is_in_stack_list(stack_name):
            stack = OpenstackStackListKeywords(self.ssh_connection).get_openstack_stack_list().get_stack(stack_name)
            return stack.get_stack_status() == OpenstackStackStatusEnum.UPDATE_IN_PROGRESS.value or stack.get_stack_status() == OpenstackStackStatusEnum.UPDATE_COMPLETE.value
        return False

    def get_command(self, openstack_stack_update_input: OpenstackStackUpdateInput) -> str:
        """
        Generates the 'openstack stack update' command using values from the given input object.

        Args:
            openstack_stack_update_input (OpenstackStackUpdateInput): Input parameters for the update command

        Returns:
            str: a string representing the 'openstack stack update' command, configured according to the parameters in the 'openstack_stack_update_input' argument.
        """
        # 'template_file_path' and 'template_file_name' properties are required
        template_file_path = openstack_stack_update_input.get_template_file_path()
        template_file_name = openstack_stack_update_input.get_template_file_name()
        if String.is_empty(template_file_path) or String.is_empty(template_file_name):
            error_message = "Template path and name must be specified"
            get_logger().log_exception(error_message)
            raise ValueError(error_message)
        template_file_path_as_param = f"--template={openstack_stack_update_input.get_template_file_path()}/{openstack_stack_update_input.get_template_file_name()}"

        # 'stack_name' is required
        stack_name = openstack_stack_update_input.get_stack_name()
        if String.is_empty(stack_name):
            error_message = "Stack name is required"
            get_logger().log_exception(error_message)
            raise ValueError(error_message)

        # 'return_format' property is optional.
        return_format_as_param = f"-f {openstack_stack_update_input.get_return_format()}"

        # Assembles the command.
        cmd = f"openstack stack update {return_format_as_param} {template_file_path_as_param} {stack_name}"

        return cmd
