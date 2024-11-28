from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.servicegroup.objects.system_servicegroup_object import SystemServiceGroupOutput


class SystemServiceGroupKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system servicegroup-*' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_servicegroup_list(self) -> SystemServiceGroupOutput:
        """
        Gets the system servicegroup list

        Returns: SystemServiceGroupOutput

        """
        output = self.ssh_connection.send(source_openrc('system servicegroup-list'))
        self.validate_success_return_code(self.ssh_connection)
        system_servicegroup_output = SystemServiceGroupOutput(output)

        return system_servicegroup_output
