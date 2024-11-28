from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.controllerfs.objects.system_controllerfs_output import SystemControllerFSOutput

class SystemControllerFSKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system controllerfs-list' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_controllerfs_list(self) -> SystemControllerFSOutput:
        """
        Gets the system controllerfs list

        Returns:
            SystemControllerFSOutput object with the list of controllerfs.

        """
        command = source_openrc('system controllerfs-list')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_controllerfs_output = SystemControllerFSOutput(output)
        return system_controllerfs_output


