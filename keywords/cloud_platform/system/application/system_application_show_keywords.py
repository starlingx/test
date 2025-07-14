from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry, validate_str_contains_with_retry
from framework.validation.validation_response import ValidationResponse
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.application.object.system_application_show_object import SystemApplicationShowObject
from keywords.cloud_platform.system.application.object.system_application_show_output import SystemApplicationShowOutput


class SystemApplicationShowKeywords(BaseKeyword):
    """
    Provides methods to interact with the 'system application-show' command

    Methods:
        get_system_application_show(app_name): Run the command and parse output
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): The SSH connection object
        """
        self.ssh_connection = ssh_connection

    def get_system_application_show(self, app_name: str) -> SystemApplicationShowOutput:
        """
        Executes the 'system application-show <app_name>' command and returns parsed output

        Args:
            app_name (str): The application name to query

        Returns:
            SystemApplicationShowOutput: The parsed output from the command

        Raises:
            Exception: If the command execution or parsing fails
        """
        try:
            cmd = f"system application-show {app_name}"
            output = self.ssh_connection.send(source_openrc(cmd))
            self.validate_success_return_code(self.ssh_connection)
            return SystemApplicationShowOutput(output)
        except Exception as ex:
            get_logger().log_exception(f"Failed to run 'system application-show {app_name}'")
            raise ex

    def validate_app_status(self, app_name: str, expected_status: str) -> SystemApplicationShowObject:
        """
        Validates that the application reaches the expected status.

        Args:
            app_name (str): Name of the application
            expected_status (str): Expected status (e.g., 'applied')

        Returns:
            SystemApplicationShowObject:
        """

        def get_status():
            system_application_object = self.get_system_application_show(app_name).get_system_application_object()
            return ValidationResponse(system_application_object.get_status(), system_application_object)

        return validate_equals_with_retry(get_status, expected_status, f"Application '{app_name}' status is '{expected_status}'", timeout=300)

    def validate_app_active(self, app_name: str, expected_active: str) -> SystemApplicationShowObject:
        """
        Validates that the application reaches the expected active.

        Args:
            app_name (str): Name of the application
            expected_active (str): Expected active state (e.g., 'True')

        Returns:
            SystemApplicationShowObject:
        """

        def get_active():
            system_application_object = self.get_system_application_show(app_name).get_system_application_object()
            return ValidationResponse(system_application_object.get_active(), system_application_object)

        return validate_equals_with_retry(get_active, expected_active, f"Application '{app_name}' active value is '{expected_active}'", timeout=300)

    def validate_app_progress_contains(self, app_name: str, expected_progress: str) -> SystemApplicationShowObject:
        """
        Validates that the application reaches the expected progress.

        Args:
            app_name (str): Name of the application
            expected_progress (str): Expected progress (e.g., 'completed')

        Returns:
            SystemApplicationShowObject:
        """

        def get_progress():
            system_application_object = self.get_system_application_show(app_name).get_system_application_object()
            return ValidationResponse(system_application_object.get_progress(), system_application_object)

        return validate_str_contains_with_retry(get_progress, expected_progress, f"Application '{app_name}' progress is '{expected_progress}'", timeout=300)
