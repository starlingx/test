from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.oam.objects.system_oam_show_object import SystemOamShowObject
from keywords.cloud_platform.system.oam.objects.system_oam_show_output import SystemOamShowOutput


class SystemOamShowKeywords(BaseKeyword):
    """
    Class for System Oam Keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def oam_show(self) -> SystemOamShowObject:
        """
        Keyword for system oam show command
        Args:

        Returns:

        """
        output = self.ssh_connection.send(source_openrc('system oam-show'))
        self.validate_success_return_code(self.ssh_connection)
        system_host_output = SystemOamShowOutput(output)

        return system_host_output.system_oam_show_object
