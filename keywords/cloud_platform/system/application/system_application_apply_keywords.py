from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.application.object.system_application_apply_input import SystemApplicationApplyInput
from keywords.cloud_platform.system.application.object.system_application_list_status_tracking_input import SystemApplicationListStatusTrackingInput
from keywords.cloud_platform.system.application.object.system_application_output import SystemApplicationOutput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.python.string import String


class SystemApplicationApplyKeywords(BaseKeyword):
    """
    Class for System application keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def system_application_apply(self, system_application_apply_input: SystemApplicationApplyInput) -> SystemApplicationOutput:
        """
        Executes the applying of an application file by executing the command 'system application-apply'. This method
        returns upon the completion of the 'system application-apply' command, that is, when the 'status' is 'applied'.

        Executes the installation of an application by executing the command 'system application-apply'.
        Args:
            system_application_apply_input (SystemApplicationApplyInput): the object representing the parameters for
            executing the 'system application-apply' command.

        Returns:
            SystemApplicationOutput: an object representing status values related to the current installation
            process of the application, as a result of the execution of the 'system application-apply' command.

        """
        # Gets the app name.
        app_name = system_application_apply_input.get_app_name()

        # Gets the command 'system application-apply' with its parameters configured.
        cmd = self.get_command(system_application_apply_input)

        # Executes the command 'system application-apply'.
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        system_application_output = SystemApplicationOutput(output)

        # Tracks the execution of the command 'system application-apply' until its completion or a timeout.

        # Setups the status tracker.
        system_application_list_status_tracking_input = SystemApplicationListStatusTrackingInput(app_name, SystemApplicationStatusEnum.APPLIED)
        system_application_list_status_tracking_input.set_timeout_in_seconds(system_application_apply_input.get_timeout_in_seconds())
        system_application_list_status_tracking_input.set_check_interval_in_seconds(system_application_apply_input.get_check_interval_in_seconds())

        # Tracks the status of the application.
        system_application_list_keywords = SystemApplicationListKeywords(self.ssh_connection)
        system_application_list_output = system_application_list_keywords.track_status(system_application_list_status_tracking_input)

        # If the execution arrived here the status of the application is 'applied'.
        application = system_application_list_output.get_application(app_name)
        system_application_output.get_system_application_object().set_status(application.get_status())

        return system_application_output

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

    def get_command(self, system_application_apply_input: SystemApplicationApplyInput) -> str:
        """
        Generates a string representing the 'system application-apply' command with parameters based on the values in
        the 'system_application_apply_input' argument.
        Args:
            system_application_apply_input (SystemApplicationApplyInput): an instance of SystemApplicationApplyInput
            configured with the parameters needed to execute the 'system application-apply' command properly.

        Returns:
            str: a string representing the 'system application-apply' command, configured according to the parameters in
            the 'system_application_apply_input' argument.

        """
        app_name_as_param = system_application_apply_input.get_app_name()
        if String.is_empty(app_name_as_param):
            error_message = "The app_name property must be specified."
            get_logger().log_exception(error_message)
            raise ValueError(error_message)

        # Assembles the command 'system application-apply'.
        cmd = f'system application-apply {app_name_as_param}'

        return cmd
