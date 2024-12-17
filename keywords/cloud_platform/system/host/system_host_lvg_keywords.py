from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_lvg_output import SystemHostLvgOutput
from keywords.cloud_platform.system.host.objects.system_host_lvg_show_output import SystemHostLvgShowOutput


class SystemHostLvgKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-lvg' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_host_lvg_list(self, host_id) -> SystemHostLvgOutput:
        """
        Gets the system host-lvg-list

        Args:
            host_id: name or id of the host
        Returns:
            SystemHostLvgOutput object with the list of host-lvg.

        """
        command = source_openrc(f'system host-lvg-list {host_id}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_lvg_output = SystemHostLvgOutput(output)
        return system_host_lvg_output

    def get_system_host_lvg_show(self, host_id, lvg_name) -> SystemHostLvgShowOutput:
        """
        Gets the system host-lvg-show

        Args:
            host_id: name or id of the host
            lvg_name: name or uuid of lvg
        Returns:
            SystemHostLvgShowOutput object.

        """
        command = source_openrc(f'system host-lvg-show {host_id} {lvg_name}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_lvg_output = SystemHostLvgShowOutput(output)
        return system_host_lvg_output

