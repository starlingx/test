from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_device_output import SystemHostDeviceOutput


class SystemHostDeviceKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-device-*' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_host_device_list(self, hostname) -> SystemHostDeviceOutput:
        """
        Gets the system host device list

        Args:
            hostname: Name of the host for which we want to get the device list.

        Returns: SystemHostDeviceOutput

        """
        output = self.ssh_connection.send(source_openrc(f'system host-device-list --nowrap {hostname}'))
        self.validate_success_return_code(self.ssh_connection)
        system_host_device_output = SystemHostDeviceOutput(output)

        return system_host_device_output
