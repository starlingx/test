from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.kubernetes.object.kubernetes_version_list_output import KubernetesVersionListOutput


class SystemKubernetesListKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system kube-version-list' command.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor

        Args:
            ssh_connection (SSHConnection): ssh object

        """
        self.ssh_connection = ssh_connection

    def get_system_kube_version_list(self) -> KubernetesVersionListOutput:
        """Gets the 'system kube-version-list' output.

        Returns:
            KubernetesVersionListOutput: a KubernetesVersionListOutput object representing
            the output of the command 'dcmanager kube-version-list list'.

        """
        output = self.ssh_connection.send(source_openrc("system kube-version-list"))
        self.validate_success_return_code(self.ssh_connection)

        kubernetes_version_list_output = KubernetesVersionListOutput(output)

        return kubernetes_version_list_output

    def get_kubernetes_versions_by_state(self, state: str) -> list:
        """
        Retrieves the kubernetes available versions filtered by state.

        Args:
            state (str): Desires kubernetes version state.

        Returns:
            list: List of kubernetes versions.
        """
        return self.get_system_kube_version_list().get_version_by_state(state)

    def get_all_kubernetes_versions(self) -> list:
        """
        Retrieves all kubernetes versions.

        Returns:
            list: List of kubernetes versions.
        """
        return self.get_system_kube_version_list().get_kubernetes_version()
