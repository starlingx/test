from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.service.objects.system_service_output import SystemServiceOutput
from keywords.cloud_platform.system.service.objects.system_service_show_output import SystemServiceShowOutput


class SystemServiceKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system service' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_service_list(self) -> SystemServiceOutput:
        """
        Gets the system service-list

        Args:

        Returns:
            SystemServiceOutput object with the list of service.

        """
        command = source_openrc(f'system service-list')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_service_output = SystemServiceOutput(output)
        return system_service_output

    def get_system_service_show(self, service_id) -> SystemServiceShowOutput:
        """
        Gets the system service-show

        Args:
            service_id: service_id

        Returns:
            SystemServiceShowOutput object.

        """
        command = source_openrc(f'system service-show {service_id}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_service_show_output = SystemServiceShowOutput(output)
        return system_service_show_output