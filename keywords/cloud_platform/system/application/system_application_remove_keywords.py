from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.application.object.system_application_list_status_tracking_input import SystemApplicationListStatusTrackingInput
from keywords.cloud_platform.system.application.object.system_application_output import SystemApplicationOutput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords


class SystemApplicationRemoveKeywords(BaseKeyword):
    """
    Class for System application remove keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def system_application_remove(self, system_application_remove_input: SystemApplicationRemoveInput) -> SystemApplicationOutput:
        """
        Remove an application specified in the parameter 'system_application_remove_input'.
        Args:
            system_application_remove_input (SystemApplicationRemoveInput): defines the application name and if the
            removing must be forced or not.

        Returns:
            SystemApplicationOutput:
        """
        # Gets the app name.
        app_name = system_application_remove_input.get_app_name()

        # Gets the command 'system application-remove' with its parameters configured.
        cmd = self.get_command(system_application_remove_input)

        # Executes the command 'system application-remove'
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        system_application_output = SystemApplicationOutput(output)

        # Tracks the execution of the command 'system application-apply' until its completion or a timeout.

        # Setups the status tracker. Note: there's no 'removed' status. When an app is removed its status comes back to 'uploaded'.
        system_application_list_status_tracking_input = SystemApplicationListStatusTrackingInput(app_name, SystemApplicationStatusEnum.UPLOADED)
        system_application_list_status_tracking_input.set_timeout_in_seconds(system_application_remove_input.get_timeout_in_seconds())
        system_application_list_status_tracking_input.set_check_interval_in_seconds(system_application_remove_input.get_check_interval_in_seconds())

        # Tracks the status of the application.
        system_application_list_keywords = SystemApplicationListKeywords(self.ssh_connection)
        system_application_list_output = system_application_list_keywords.track_status(system_application_list_status_tracking_input)

        # If the execution arrived here the status of the application is 'uploaded', that is, the application was removed.
        application = system_application_list_output.get_application(app_name)
        system_application_output.get_system_application_object().set_status(application.get_status())

        return system_application_output

    def get_command(self, system_application_remove_input: SystemApplicationRemoveInput) -> str:
        """
        Generates a string representing the 'system application-remove' command with parameters based on the values in
        the 'system_application_remove_input' argument.
        Args:
            system_application_remove_input (SystemApplicationRemoveInput): an instance of SystemApplicationRemoveInput
            configured with the parameters needed to execute the 'system application-remote' command properly.

        Returns:
            str: a string representing the 'system application-remote' command, configured according to the parameters
            in the 'system_application_remote_input' argument.

        """
        force_as_param = ''
        if system_application_remove_input.get_force_removal():
            force_as_param = '-f'

        cmd = f'system application-remove {force_as_param} {system_application_remove_input.get_app_name()}'
        return cmd
