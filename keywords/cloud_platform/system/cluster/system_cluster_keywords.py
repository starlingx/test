from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.cluster.objects.system_cluster_output import SystemClusterOutput
from keywords.cloud_platform.system.cluster.objects.system_cluster_show_output import SystemClusterShowOutput


class SystemClusterKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system cluster' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_cluster_list(self) -> SystemClusterOutput:
        """
        Gets the system cluster-list

        Args:

        Returns:
            SystemClusterOutput object with the list of cluster.

        """
        command = source_openrc(f'system cluster-list')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_cluster_output = SystemClusterOutput(output)
        return system_cluster_output

    def get_system_cluster_show(self, uuid) -> SystemClusterShowOutput:
        """
        Gets the system cluster-show

        Args:
            uuid: uuid of the cluster

        Returns:
            SystemClusterShowOutput object.

        """
        command = source_openrc(f'system cluster-show {uuid}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_cluster_show_output = SystemClusterShowOutput(output)
        return system_cluster_show_output