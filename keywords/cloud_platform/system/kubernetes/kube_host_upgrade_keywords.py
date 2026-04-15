from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.kubernetes.object.kube_host_upgrade_output import KubeHostUpgradeOutput


class KubeHostUpgradeKeywords(BaseKeyword):
    """Keywords for the 'system kube-host-upgrade' command."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def kube_host_upgrade_control_plane(self, host: str) -> KubeHostUpgradeOutput:
        """Executes the 'system kube-host-upgrade {host} control-plane' command.

        Args:
            host (str): Hostname to upgrade the control plane on.

        Returns:
            KubeHostUpgradeOutput: Parsed output of the command.
        """
        output = self.ssh_connection.send(source_openrc(f"system kube-host-upgrade {host} control-plane"))
        self.validate_success_return_code(self.ssh_connection)
        return KubeHostUpgradeOutput(output)

    def kube_host_upgrade_kubelet(self, host: str) -> KubeHostUpgradeOutput:
        """Executes the 'system kube-host-upgrade {host} kubelet' command.

        Args:
            host (str): Hostname to upgrade kubelet on.

        Returns:
            KubeHostUpgradeOutput: Parsed output of the command.
        """
        output = self.ssh_connection.send(source_openrc(f"system kube-host-upgrade {host} kubelet"))
        self.validate_success_return_code(self.ssh_connection)
        return KubeHostUpgradeOutput(output)
