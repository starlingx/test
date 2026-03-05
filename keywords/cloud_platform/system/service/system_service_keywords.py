from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.service.objects.system_service_output import SystemServiceOutput
from keywords.cloud_platform.system.service.objects.system_service_show_output import SystemServiceShowOutput


class SystemServiceKeywords(BaseKeyword):
    """Keywords related to the 'system service' commands.

    Args:
        ssh_connection (SSHConnection): SSH connection instance
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def get_system_service_list(self) -> SystemServiceOutput:
        """
        Gets the system service-list.

        Returns:
            SystemServiceOutput: Object with the list of service.
        """
        command = source_openrc("system service-list")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_service_output = SystemServiceOutput(output)
        return system_service_output

    def get_system_service_show(self, service_id: str) -> SystemServiceShowOutput:
        """
        Gets the system service-show.

        Args:
            service_id (str): Service ID

        Returns:
            SystemServiceShowOutput: Service show output object.
        """
        command = source_openrc(f"system service-show {service_id}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_service_show_output = SystemServiceShowOutput(output)
        return system_service_show_output
