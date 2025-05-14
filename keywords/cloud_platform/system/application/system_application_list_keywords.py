from typing import List

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry, validate_list_contains_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.application.object.system_application_list_output import SystemApplicationListOutput


class SystemApplicationListKeywords(BaseKeyword):
    """
    Class for System application list keywords.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor

        Args:
            ssh_connection (SSHConnection): ssh object

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
        output = self.ssh_connection.send(source_openrc("system application-list"))
        self.validate_success_return_code(self.ssh_connection)
        system_application_list_output = SystemApplicationListOutput(output)

        return system_application_list_output

    def validate_app_status(self, application_name: str, status: str, timeout: int = 300, polling_sleep_time: int = 5):
        """This function will validate that the application specified reaches the desired status.

        Args:
            application_name (str): Name of the application that we are waiting for.
            status (str): Status in which we want to wait for the application to reach.
            timeout (int): Timeout in seconds
            polling_sleep_time (int): wait time in seconds before the next attempt when unsuccessful validation

        Returns: None

        """

        def get_app_status():
            system_applications = self.get_system_application_list()
            application_status = system_applications.get_application(application_name).get_status()
            return application_status

        message = f"Application {application_name}'s status is {status}"
        validate_equals_with_retry(get_app_status, status, message, timeout, polling_sleep_time)

    def validate_app_status_in_list(self, application_name: str, status: List[str], timeout: int = 3600, polling_sleep_time: int = 30) -> str:
        """This function will validate that the application specified reaches the desired status.

        Args:
            application_name (str): Name of the application that we are waiting for.
            status (List[str]): Status in which we want to wait for the application to reach.
            timeout (int): Timeout in seconds
            polling_sleep_time (int): wait time in seconds before the next attempt when unsuccessful validation

        Returns:
            str: observed_status of the application

        """

        def get_app_status():
            system_applications = self.get_system_application_list()
            application_status = system_applications.get_application(application_name).get_status()
            return application_status

        message = f"Application {application_name}'s status is in {status}"
        observed_status = validate_list_contains_with_retry(get_app_status, status, message, timeout, polling_sleep_time)
        return observed_status

    def is_app_present(self, application_name: str) -> bool:
        """This function will validate that the application is present in application list.

        Args:
            application_name (str): Name of the application that we want to check.

        Returns:
            bool: True if application is found in list else False
        """
        try:
            system_applications = self.get_system_application_list()
            application_status = system_applications.get_application(application_name).get_status()
            get_logger().log_info(f"{application_name} is present. Status is {application_status}")
            return True

        except KeywordException:
            get_logger().log_info(f"{application_name} is not found.")
            return False

    def validate_all_apps_status(self, expected_statuses: [str]) -> bool:
        """Validates That all apps are in the expected status.

        Args:
            expected_statuses ([str]): list of expected statuses ex. ['applied' , 'uploaded']

        Returns:
            bool: True if all apps are in the expected status, False otherwise.
        """
        apps = self.get_system_application_list().get_applications()
        not_applied_apps = list(filter(lambda app: app.get_status() not in expected_statuses, apps))
        if len(not_applied_apps) == 0:
            return True
        else:
            for app in not_applied_apps:
                get_logger().log_info(f"Application {app.get_application()} is in status {app.get_status()}")
            raise KeywordException("All applications are not in the expected status.")
