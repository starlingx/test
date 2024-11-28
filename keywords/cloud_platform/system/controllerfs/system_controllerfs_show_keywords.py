from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.controllerfs.objects.system_controller_fs_show_output import SystemControllerFSShowOutput


class SystemControllerFSShowKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system controllerfs-show <controller-fs name>' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_controllerfs_show(self, controllerfs_name) -> SystemControllerFSShowOutput:
        """
        Gets the system controllerfs-show <controller-fs name>

        Returns:
            SystemControllerFSShowOutput object with the attributes of controllerfs.

        """
        command = source_openrc(f'system controllerfs-show {controllerfs_name}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_controllerfs_output = SystemControllerFSShowOutput(output)
        return system_controllerfs_output


