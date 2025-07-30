from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.openstack.command_wrappers import source_admin_openrc
from keywords.openstack.openstack.stack.object.openstack_stack_create_input import OpenstackStackCreateInput
from keywords.openstack.openstack.stack.object.openstack_stack_output import OpenstackStackOutput
from keywords.openstack.openstack.stack.object.openstack_stack_status_enum import OpenstackStackStatusEnum
from keywords.openstack.openstack.stack.openstack_stack_list_keywords import OpenstackStackListKeywords
from keywords.python.string import String


class OpenstackStackCreateKeywords(BaseKeyword):
    """Class for Openstack Stack Create Keywords"""

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor for OpenstackStackCreateKeywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller
        """
        self.ssh_connection = ssh_connection

    def openstack_stack_create(self, openstack_stack_create_input: OpenstackStackCreateInput) -> OpenstackStackOutput:
        """
        Openstack stack create function, creates a given stack

        Args:
            openstack_stack_create_input (OpenstackStackCreateInput): an object with the required parameters

        Returns:
            OpenstackStackOutput: the output of the openstack stack create command
        """
        # Gets the command 'openstack stack create' with its parameters configured.
        cmd = self.get_command(openstack_stack_create_input)
        stack_name = openstack_stack_create_input.get_stack_name()

        # Executes the command 'openstack stack create'.
        output = self.ssh_connection.send(source_admin_openrc(cmd), get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        openstack_stack_output = OpenstackStackOutput(output)

        # Tracks the execution of the command 'openstack stack create' until its completion or a timeout.
        openstack_stack_list_keywords = OpenstackStackListKeywords(self.ssh_connection)
        openstack_stack_list_keywords.validate_stack_status(stack_name, "CREATE_COMPLETE")

        # If the execution arrived here the status of the stack is 'created'.
        openstack_stack_output.get_openstack_stack_object().set_stack_status("create_complete")

        return openstack_stack_output

    def is_already_created(self, stack_name: str) -> bool:
        """
        Verifies if the stack has already been created.

        Args:
            stack_name (str): a string representing the name of the stack.

        Returns:
            bool: True if the stack named 'stack_name' has already been created; False otherwise.
        """
        try:
            openstack_stack_list_keywords = OpenstackStackListKeywords(self.ssh_connection)
            if openstack_stack_list_keywords.get_openstack_stack_list().is_in_stack_list(stack_name):
                stack = OpenstackStackListKeywords(self.ssh_connection).get_openstack_stack_list().get_stack(stack_name)
                return stack.get_stack_status() == OpenstackStackStatusEnum.CREATE_IN_PROGRESS.value or stack.get_stack_status() == OpenstackStackStatusEnum.CREATE_COMPLETE.value or stack.get_stack_status() == OpenstackStackStatusEnum.UPDATE_IN_PROGRESS.value or stack.get_stack_status() == OpenstackStackStatusEnum.UPDATE_COMPLETE.value or stack.get_stack_status() == OpenstackStackStatusEnum.ROLLBACK_IN_PROGRESS.value or stack.get_stack_status() == OpenstackStackStatusEnum.ROLLBACK_COMPLETE.value
            return False
        except Exception as ex:
            get_logger().log_exception(f"An error occurred while verifying whether the application named {stack_name} is already created.")
            raise ex

    def get_command(self, openstack_stack_create_input: OpenstackStackCreateInput) -> str:
        """
        Generates the 'openstack stack create' command using values from the given input object.

        Args:
            openstack_stack_create_input (OpenstackStackCreateInput): Input parameters for the create command

        Returns:
            str: a string representing the 'openstack stack create' command, configured according to the parameters in the 'openstack_stack_create_input' argument.
        """
        # 'template_file_path' and 'template_file_name' properties are required
        template_file_path = openstack_stack_create_input.get_template_file_path()
        template_file_name = openstack_stack_create_input.get_template_file_name()
        if String.is_empty(template_file_path) or String.is_empty(template_file_name):
            error_message = "Template path and name must be specified"
            get_logger().log_exception(error_message)
            raise ValueError(error_message)
        template_file_path_as_param = f"--template={openstack_stack_create_input.get_template_file_path()}/{openstack_stack_create_input.get_template_file_name()}"

        # 'stack_name' is required
        stack_name = openstack_stack_create_input.get_stack_name()
        if String.is_empty(stack_name):
            error_message = "Stack name is required"
            get_logger().log_exception(error_message)
            raise ValueError(error_message)

        # 'return_format' property is optional.
        return_format_as_param = f"-f {openstack_stack_create_input.get_return_format()}"

        # Assembles the command.
        cmd = f"openstack stack create {return_format_as_param} {template_file_path_as_param} {stack_name}"

        return cmd
