import time

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.application.object.system_application_list_output import SystemApplicationListOutput
from keywords.cloud_platform.system.application.object.system_application_list_status_tracking_input import SystemApplicationListStatusTrackingInput


class SystemApplicationListKeywords(BaseKeyword):
    """
    Class for System application list keywords.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_application_list(self) -> SystemApplicationListOutput:
        """
        Gets a SystemApplicationOutput object related to the execution of the 'system application-list' command.

        Args: None

        Returns:
             SystemApplicationListOutput: an instance of the SystemApplicationOutput object representing the
             applications on the host, as a result of the execution of the 'system application-list' command.
        """
        output = self.ssh_connection.send(source_openrc('system application-list'))
        self.validate_success_return_code(self.ssh_connection)
        system_application_list_output = SystemApplicationListOutput(output)

        return system_application_list_output

    def track_status(self, system_application_list_status_tracking_input: SystemApplicationListStatusTrackingInput) -> SystemApplicationListOutput:
        """

        Args:
            system_application_list_status_tracking_input:

        Returns:
             SystemApplicationListOutput: an instance of the SystemApplicationOutput object representing the
             applications on the host, as a result of the execution of the 'system application-list' command.
             If no exception is raised during the execution of this method, the 'status' property of this instance will
             have the same value as defined in the 'system_application_list_status_tracking_input' argument.

        """
        system_application_list_output = None

        # Gets the input values.
        expected_status = system_application_list_status_tracking_input.get_expected_status()
        app_name = system_application_list_status_tracking_input.get_app_name()
        check_interval_in_seconds = system_application_list_status_tracking_input.get_check_interval_in_seconds()
        timeout_in_seconds = system_application_list_status_tracking_input.get_timeout_in_seconds()

        # Tracks the target status.
        timeout = True
        end_time = time.time() + timeout_in_seconds
        while time.time() < end_time:
            system_application_list_output = self.get_system_application_list()
            system_application_list_object = system_application_list_output.get_application(app_name)
            if system_application_list_object is not None:
                if system_application_list_object.get_status() == expected_status.value:
                    timeout = False
                    get_logger().log_info(f"Application {app_name} reached the '{system_application_list_object.get_status()}' status.")
                    break
                else:
                    get_logger().log_info(
                        f"Waiting for {check_interval_in_seconds} more seconds to the application {app_name} to reach the {expected_status.value} status. Maximum total time to wait: {timeout_in_seconds} s. Remaining time: {end_time - time.time():.3f} s. Current status: '{system_application_list_object.get_status()}'."
                    )
                    time.sleep(check_interval_in_seconds)

        # Verifies whether a timeout has occurred.
        if timeout:
            message = f"Application {app_name} couldn't reach the expected status {expected_status.value}. Reason: timeout ({timeout_in_seconds} s). Note: the expected process was not interrupted."
            raise TimeoutError(message)

        return system_application_list_output

    def validate_app_status(self, application_name: str, status: str):
        """
        This function will validate that the application specified reaches the desired status.
        Args:
            application_name: Name of the application that we are waiting for.
            status: Status in which we want to wait for the application to reach.

        Returns: None

        """

        def get_app_status():
            system_applications = self.get_system_application_list()
            application_status = system_applications.get_application(application_name).get_status()
            return application_status

        message = f"Application {application_name}'s status is {status}"
        validate_equals_with_retry(get_app_status, status, message)

