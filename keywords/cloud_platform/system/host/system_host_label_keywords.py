from typing import List

from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_label_assign_output import SystemHostLabelAssignOutput
from keywords.cloud_platform.system.host.objects.system_host_label_list_output import SystemHostLabelListOutput


class SystemHostLabelKeywords(BaseKeyword):
    """
    Keywords for System Host Label List
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_host_label_list(self, host_name: str) -> SystemHostLabelListOutput:
        """
        Gets the system host label list
        Args:
            host_name (): the host name to run the command for

        Returns: SystemHostLabelListOutput

        """
        output = self.ssh_connection.send(source_openrc(f'system host-label-list {host_name}'))
        self.validate_success_return_code(self.ssh_connection)
        system_host_label_list_output = SystemHostLabelListOutput(output)

        return system_host_label_list_output

    def system_host_label_assign(self, host_name: str, labels: str) -> SystemHostLabelAssignOutput:
        """
        This function will run the 'system host-label-assign <host_name> <labels>' command
        Args:
            host_name: The name of the host on which we want to assign labels.
            labels: The space-separated list of label_key=label_value

        Returns: SystemHostLabelAssignOutput

        """
        output = self.ssh_connection.send(source_openrc(f'system host-label-assign {host_name} {labels}'))
        self.validate_success_return_code(self.ssh_connection)
        system_host_label_assign_output = SystemHostLabelAssignOutput(output)

        return system_host_label_assign_output

    def system_host_label_remove(self, host_name: str, labels: str) -> List[str]:
        """
        This function will run the 'system host-label-remove <host_name> <labels>' command
        Args:
            host_name: The name of the host on which we want to remove labels.
            labels: The space-separated list of label_key

        Returns:
            A list of Strings for each label removed. e.g.
            ["Deleted host label kube-cpu-mgr-policy for host controller-0",
             "Deleted host label kube-topology-mgr-policy for host controller-0"]

        """
        output = self.ssh_connection.send(source_openrc(f'system host-label-remove {host_name} {labels}'))
        self.validate_success_return_code(self.ssh_connection)

        return output
