from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.application.object.system_application_output import SystemApplicationOutput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.object.system_application_update_input import SystemApplicationUpdateInput
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.python.string import String


class SystemApplicationUpdateKeywords(BaseKeyword):
    """
    Class for System application update keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSH connection object

        """
        self.ssh_connection = ssh_connection

    def system_application_update(self, system_application_update_input: SystemApplicationUpdateInput) -> SystemApplicationOutput:
        """
        Executes the update of an application by executing the command 'system application-update'.

        This method returns upon the completion of the 'system application-update' command, that is, when the 'status' is 'applied'.

        Args:
            system_application_update_input (SystemApplicationUpdateInput): the object representing the parameters for
                executing the 'system application-update' command.

        Returns:
            SystemApplicationOutput: an object representing status values related to the current updating process of
                the application, as a result of the execution of the 'system application-update' command.

        """
        # Gets the command 'system application-update' with its parameters configured.
        cmd = self.get_command(system_application_update_input)

        # Determine app name for status tracking
        app_name = system_application_update_input.get_app_name()

        # Executes the command 'system application-update'.
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        system_application_output = SystemApplicationOutput(output)

        # Tracks the execution of the command 'system application-update' until its completion or a timeout.
        system_application_list_keywords = SystemApplicationListKeywords(self.ssh_connection)
        system_application_list_keywords.validate_app_status(app_name, SystemApplicationStatusEnum.APPLIED.value)

        # If the execution arrived here the status of the application is 'applied'.
        system_application_output.get_system_application_object().set_status(SystemApplicationStatusEnum.APPLIED.value)

        return system_application_output

    def get_command(self, system_application_update_input: SystemApplicationUpdateInput) -> str:
        """
        Generates a string representing the 'system application-update' command with parameters.

        Based on the values in the 'system_application_update_input' argument.

        Args:
            system_application_update_input (SystemApplicationUpdateInput): an instance of SystemApplicationUpdateInput
                configured with the parameters needed to execute the 'system application-update' command properly.

        Returns:
            str: a string representing the 'system application-update' command, configured according to the parameters
                in the 'system_application_update_input' argument.

        """
        # Either 'tar_file_path' or 'app_name' property is required.
        tar_file_path = system_application_update_input.get_tar_file_path()
        app_name = system_application_update_input.get_app_name()

        if String.is_empty(tar_file_path) and String.is_empty(app_name):
            error_message = "Either tar_file_path or app_name property must be specified."
            get_logger().log_exception(error_message)
            raise ValueError(error_message)

        # Assembles the command - prioritize tar_file_path if provided
        if not String.is_empty(tar_file_path):
            cmd = f"system application-update {tar_file_path}"
        else:
            cmd = f"system application-update {app_name}"

        return cmd
