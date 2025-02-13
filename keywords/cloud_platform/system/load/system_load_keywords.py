from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.load.objects.system_load_show_output import SystemLoadShowOutput


class SystemLoadKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system load' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_load_show(self, load_id:int) -> SystemLoadShowOutput:
        """
        Gets the system load-show

        Args:
        load_id (int): load id.

        Returns:
            SystemLoadShowOutput object.

        """
        command = source_openrc(f'system load-show {load_id}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_load_show_output = SystemLoadShowOutput(output)
        return system_load_show_output