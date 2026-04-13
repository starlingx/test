from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.application.object.system_application_output import SystemApplicationOutput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords


class SystemApplicationRemoveKeywords(BaseKeyword):
    """
    Class for System application remove keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def system_application_remove(self, system_application_remove_input: SystemApplicationRemoveInput) -> SystemApplicationOutput:
        """
        Remove an application specified in the parameter 'system_application_remove_input'.

        Args:
            system_application_remove_input (SystemApplicationRemoveInput): defines the application name, timeout,
                check interval, and if the removing must be forced or not.

        Returns:
            SystemApplicationOutput: the output of the system application-remove command.
        """
        # Gets the app name.
        app_name = system_application_remove_input.get_app_name()

        # Gets the command 'system application-remove' with its parameters configured.
        cmd = self.get_command(system_application_remove_input)

        # Executes the command 'system application-remove'
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        system_application_output = SystemApplicationOutput(output)

        # Tracks the execution of the command 'system application-remove' until its completion or a timeout.
        system_application_list_keywords = SystemApplicationListKeywords(self.ssh_connection)
        timeout = system_application_remove_input.get_timeout_in_seconds()
        check_interval = system_application_remove_input.get_check_interval_in_seconds()
        system_application_list_keywords.validate_app_status(app_name, "uploaded", timeout, check_interval)

        # If the execution arrived here the status of the application is 'uploaded', that is, the application was removed.
        system_application_output.get_system_application_object().set_status("uploaded")

        return system_application_output

    def get_command(self, system_application_remove_input: SystemApplicationRemoveInput) -> str:
        """
        Generates a string representing the 'system application-remove' command with parameters.

        Args:
            system_application_remove_input (SystemApplicationRemoveInput): an instance of SystemApplicationRemoveInput
                configured with the parameters needed to execute the 'system application-remove' command properly.

        Returns:
            str: a string representing the 'system application-remove' command, configured according to the parameters
                in the 'system_application_remove_input' argument.
        """
        force_as_param = ""
        if system_application_remove_input.get_force_removal():
            force_as_param = "-f"

        cmd = f"system application-remove {force_as_param} {system_application_remove_input.get_app_name()}"
        return cmd

    def system_application_remove_and_delete_app(self, app_name: str, force_removal: bool = False, force_deletion: bool = False, timeout_in_seconds: int = -1, check_interval_in_seconds: int = -1) -> str:
        """Remove and delete an application.

        Args:
            app_name (str): Name of the application to remove and delete.
            force_removal (bool): Whether to force the removal operation.
            force_deletion (bool): Whether to force the deletion operation.
            timeout_in_seconds (int): Timeout in seconds for the remove operation.
            check_interval_in_seconds (int): Check interval in seconds for the remove operation.

        Returns:
            str: the delete confirmation message.
        """
        remove_input = SystemApplicationRemoveInput()
        remove_input.set_app_name(app_name)
        remove_input.set_force_removal(force_removal)
        if timeout_in_seconds != -1:
            remove_input.set_timeout_in_seconds(timeout_in_seconds)
        if check_interval_in_seconds != -1:
            remove_input.set_check_interval_in_seconds(check_interval_in_seconds)
        self.system_application_remove(remove_input)

        delete_input = SystemApplicationDeleteInput()
        delete_input.set_app_name(app_name)
        delete_input.set_force_deletion(force_deletion)
        delete_message = SystemApplicationDeleteKeywords(self.ssh_connection).get_system_application_delete(delete_input)

        return delete_message

    def cleanup_app_if_present(self, app_name: str, force_removal: bool = False, force_deletion: bool = False, timeout_in_seconds: int = -1, check_interval_in_seconds: int = -1) -> None:
        """
        Remove and delete an application if it exists, handling both applied and uploaded states.

        This is a common teardown operation that safely cleans up applications.

        Args:
            app_name (str): Name of the application to clean up.
            force_removal (bool): Whether to force the removal operation.
            force_deletion (bool): Whether to force the deletion operation.
            timeout_in_seconds (int): Timeout in seconds for the remove operation.
            check_interval_in_seconds (int): Check interval in seconds for the remove operation.
        """
        app_list_kw = SystemApplicationListKeywords(self.ssh_connection)

        if not app_list_kw.is_app_present(app_name):
            get_logger().log_info(f"App {app_name} not present, skipping cleanup")
            return

        # Check if app is applied (needs remove) or just uploaded (needs delete only)
        apply_kw = SystemApplicationApplyKeywords(self.ssh_connection)

        if apply_kw.is_already_applied(app_name):
            get_logger().log_info(f"Removing and deleting {app_name} (status: applied)")
            self.system_application_remove_and_delete_app(app_name, force_removal, force_deletion, timeout_in_seconds, check_interval_in_seconds)
        else:
            get_logger().log_info(f"Deleting {app_name} (status: uploaded)")
            delete_input = SystemApplicationDeleteInput()
            delete_input.set_app_name(app_name)
            delete_input.set_force_deletion(force_deletion)
            SystemApplicationDeleteKeywords(self.ssh_connection).get_system_application_delete(delete_input)
