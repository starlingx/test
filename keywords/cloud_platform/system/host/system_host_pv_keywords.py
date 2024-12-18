from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_pv_output import SystemHostPvOutput


class SystemHostPvKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-pv' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_host_pv_list(self, host_id) -> SystemHostPvOutput:
        """
        Gets the system host-pv-list

        Args:
            host_id: name or id of the host
        Returns:
            SystemHostPvOutput object with the list of host-pv.

        """
        command = source_openrc(f'system host-pv-list {host_id}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_lvg_output = SystemHostPvOutput(output)
        return system_host_lvg_output