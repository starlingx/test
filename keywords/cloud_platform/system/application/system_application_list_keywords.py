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
        validate_equals_with_retry(get_app_status, status, message, timeout=300)

