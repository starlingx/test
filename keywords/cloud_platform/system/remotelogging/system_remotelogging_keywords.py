from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.remotelogging.objects.system_remotelogging_show_output import SystemRemoteloggingShowOutput


class SystemRemoteloggingKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system remotelogging' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_remotelogging_show(self) -> SystemRemoteloggingShowOutput:
        """
        Gets the system remotelogging-show

        Returns:
            SystemRemoteloggingShowOutput object.

        """
        command = source_openrc('system remotelogging-show')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_remotelog_show_output = SystemRemoteloggingShowOutput(output)
        return system_remotelog_show_output