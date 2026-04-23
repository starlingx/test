from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.application.object.system_application_output import SystemApplicationOutput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.python.string import String


class SystemApplicationApplyKeywords(BaseKeyword):
    """
    Class for System application keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): ssh object
        """
        self.ssh_connection = ssh_connection

    def system_application_apply(self, app_name: str, timeout: int = 300, polling_sleep_time: int = 5, wait_for_applied: bool = True) -> SystemApplicationOutput:
        """
        Executes the applying of an application file by executing the command 'system application-apply'.

        Args:
            app_name (str): the name of the application to apply
            timeout (int): Timeout in seconds
            polling_sleep_time (int): wait time in seconds before the next attempt when unsuccessful validation
            wait_for_applied (bool): whether wait for the app status from applying to applied

        Returns:
            SystemApplicationOutput: an object representing status values related to the current installation
            process of the application, as a result of the execution of the 'system application-apply' command.

        """
        # Gets the command 'system application-apply' with its parameters configured.
        cmd = self.get_command(app_name)

        # Executes the command 'system application-apply'.
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        system_application_output = SystemApplicationOutput(output)

        if wait_for_applied:
            # Tracks the execution of the command 'system application-apply' until its completion or a timeout.
            system_application_list_keywords = SystemApplicationListKeywords(self.ssh_connection)
            system_application_list_keywords.validate_app_status(app_name, "applied", timeout, polling_sleep_time, ["apply-failed"])

            # If the execution arrived here the status of the application is 'applied'.
            system_application_output.get_system_application_object().set_status("applied")

        return system_application_output

    def system_application_apply_with_retry(self, app_name: str, timeout: int = 1800, retry_interval: int = 30) -> None:
        """
        Apply an application, retrying if the command is rejected.

        Handles the case where 'system application-apply' is rejected with
        "Long running operations are in progress" by retrying until accepted.
        Once accepted, waits for the apply to complete with fail-fast on 'apply-failed'.

        Args:
            app_name (str): The application name.
            timeout (int): Total timeout in seconds.
            retry_interval (int): Seconds between retries.
        """

        def try_apply():
            cmd = self.get_command(app_name)
            self.ssh_connection.send(source_openrc(cmd))
            return self.ssh_connection.get_return_code()

        # Concern 1: retry command submission until accepted
        validate_equals_with_retry(
            try_apply,
            0,
            f"Application-apply {app_name} accepted",
            timeout=timeout,
            polling_sleep_time=retry_interval,
        )

        # Concern 2: wait for apply to complete
        SystemApplicationListKeywords(self.ssh_connection).validate_app_status(
            app_name,
            "applied",
            timeout=timeout,
            polling_sleep_time=retry_interval,
            failure_values=["apply-failed"],
        )

    def is_already_applied(self, app_name: str) -> bool:
        """
        Verifies if the application has already been applied.

        Args:
            app_name (str): a string representing the name of the application.

        Returns:
            bool: True if the application named 'app_name' has already been applied; False otherwise.

        """
        try:
            system_application_list_keywords = SystemApplicationListKeywords(self.ssh_connection)
            if system_application_list_keywords.get_system_application_list().is_in_application_list(app_name):
                application = system_application_list_keywords.get_system_application_list().get_application(app_name)
                return application.get_status() == SystemApplicationStatusEnum.APPLIED.value
            return False
        except Exception as ex:
            get_logger().log_exception(f"An error occurred while verifying whether the application named {app_name} is already applied.")
            raise ex

    def get_command(self, app_name: str) -> str:
        """
        Generates a string representing the 'system application-apply' command

        Args:
            app_name (str): Name of the application to Apply

        Returns:
            str: a string representing the 'system application-apply' command, configured according to the parameters in
            the 'system_application_apply_input' argument.

        """
        if String.is_empty(app_name):
            error_message = "The app_name property must be specified."
            get_logger().log_exception(error_message)
            raise ValueError(error_message)

        # Assembles the command 'system application-apply'.
        cmd = f"system application-apply {app_name}"

        return cmd

    def is_applied_or_failed(self, app_name: str) -> bool:
        """
        Verifies if the application has already been applied or apply-failed.

        Args:
            app_name (str): a string representing the name of the application.

        Returns:
            bool: True if the application named 'app_name' has already been applied or apply-failed; False otherwise.

        """
        system_application_list_keywords = SystemApplicationListKeywords(self.ssh_connection)
        if system_application_list_keywords.get_system_application_list().is_in_application_list(app_name):
            application = system_application_list_keywords.get_system_application_list().get_application(app_name)
            return application.get_status() == SystemApplicationStatusEnum.APPLIED.value or application.get_status() == SystemApplicationStatusEnum.APPLY_FAILED.value
        return False
