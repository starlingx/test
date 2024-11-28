from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput


class SystemApplicationDeleteKeywords(BaseKeyword):
    """
    Class for System application delete keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_application_delete(self, system_application_delete_input: SystemApplicationDeleteInput) -> str:
        """
        Delete an application specified in the parameter 'system_application_delete_input'.
        Args:
            system_application_delete_input (SystemApplicationDeleteInput): defines the application name and if the
            deletion must be forced or not.

        Returns:
            str: a string message indicating the result of the deletion. Examples:
                'Application hello-kitty deleted.\n'
                'Application-delete rejected: application not found.\n'
                'Application-delete rejected: operation is not allowed while the current status is applied.\n'
        """
        cmd = self.get_command(system_application_delete_input)
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

        return output[0]

    def get_command(self, system_application_delete_input: SystemApplicationDeleteInput) -> str:
        """
        Generates a string representing the 'system application-delete' command with parameters based on the values in
        the 'system_application_delete_input' argument.
        Args:
            system_application_delete_input (SystemApplicationDeleteInput): an instance of SystemApplicationDeleteInput
            configured with the parameters needed to execute the 'system application-delete' command properly.

        Returns:
            str: a string representing the 'system application-delete' command, configured according to the parameters
            in the 'system_application_delete_input' argument.

        """
        force_as_param = ''
        if system_application_delete_input.get_force_deletion():
            force_as_param = '-f'

        cmd = f'system application-delete {force_as_param} {system_application_delete_input.get_app_name()}'
        return cmd
