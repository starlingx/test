from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.kubernetes.object.kube_upgrade_show_output import KubeUpgradeShowOutput


class KubeUpgradeKeywords(BaseKeyword):
    """Keywords for 'system kube-upgrade' commands that return upgrade show output."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def kube_upgrade_start(self, target_kube_version: str, force: bool = False) -> KubeUpgradeShowOutput:
        """Executes the 'system kube-upgrade-start' command.

        Args:
            target_kube_version (str): Target kubernetes version to upgrade to.
            force (bool): Whether to use the --force flag.

        Returns:
            KubeUpgradeShowOutput: Parsed output of the command.
        """
        force_flag = " --force" if force else ""
        output = self.ssh_connection.send(source_openrc(f"system kube-upgrade-start{force_flag} {target_kube_version}"))
        self.validate_success_return_code(self.ssh_connection)
        return KubeUpgradeShowOutput(output)

    def kube_upgrade_start_with_error(self, target_kube_version: str, force: bool = False) -> str:
        """Executes the 'system kube-upgrade-start' command expecting an error.

        Sends the command without validating the return code, returning the
        raw output for error message validation in negative tests.

        Args:
            target_kube_version (str): Target kubernetes version to upgrade to.
            force (bool): Whether to use the --force flag.

        Returns:
            str: Raw command output containing the error message.
        """
        force_flag = " --force" if force else ""
        output = self.ssh_connection.send(source_openrc(f"system kube-upgrade-start{force_flag} {target_kube_version}"))
        self.validate_cmd_rejection_return_code(self.ssh_connection)
        return output

    def kube_upgrade_download_images(self) -> KubeUpgradeShowOutput:
        """Executes the 'system kube-upgrade-download-images' command.

        Returns:
            KubeUpgradeShowOutput: Parsed output of the command.
        """
        output = self.ssh_connection.send(source_openrc("system kube-upgrade-download-images"))
        self.validate_success_return_code(self.ssh_connection)
        return KubeUpgradeShowOutput(output)

    def kube_pre_application_update(self) -> KubeUpgradeShowOutput:
        """Executes the 'system kube-pre-application-update' command.

        Returns:
            KubeUpgradeShowOutput: Parsed output of the command.
        """
        output = self.ssh_connection.send(source_openrc("system kube-pre-application-update"))
        self.validate_success_return_code(self.ssh_connection)
        return KubeUpgradeShowOutput(output)

    def kube_post_application_update(self) -> KubeUpgradeShowOutput:
        """Executes the 'system kube-post-application-update' command.

        Returns:
            KubeUpgradeShowOutput: Parsed output of the command.
        """
        output = self.ssh_connection.send(source_openrc("system kube-post-application-update"))
        self.validate_success_return_code(self.ssh_connection)
        return KubeUpgradeShowOutput(output)

    def kube_upgrade_networking(self) -> KubeUpgradeShowOutput:
        """Executes the 'system kube-upgrade-networking' command.

        Returns:
            KubeUpgradeShowOutput: Parsed output of the command.
        """
        output = self.ssh_connection.send(source_openrc("system kube-upgrade-networking"))
        self.validate_success_return_code(self.ssh_connection)
        return KubeUpgradeShowOutput(output)

    def kube_upgrade_storage(self) -> KubeUpgradeShowOutput:
        """Executes the 'system kube-upgrade-storage' command.

        Returns:
            KubeUpgradeShowOutput: Parsed output of the command.
        """
        output = self.ssh_connection.send(source_openrc("system kube-upgrade-storage"))
        self.validate_success_return_code(self.ssh_connection)
        return KubeUpgradeShowOutput(output)

    def kube_host_cordon(self, host: str) -> KubeUpgradeShowOutput:
        """Executes the 'system kube-host-cordon' command.

        Args:
            host (str): Hostname to cordon.

        Returns:
            KubeUpgradeShowOutput: Parsed output of the command.
        """
        output = self.ssh_connection.send(source_openrc(f"system kube-host-cordon {host}"))
        self.validate_success_return_code(self.ssh_connection)
        return KubeUpgradeShowOutput(output)

    def kube_host_uncordon(self, host: str) -> KubeUpgradeShowOutput:
        """Executes the 'system kube-host-uncordon' command.

        Args:
            host (str): Hostname to uncordon.

        Returns:
            KubeUpgradeShowOutput: Parsed output of the command.
        """
        output = self.ssh_connection.send(source_openrc(f"system kube-host-uncordon {host}"))
        self.validate_success_return_code(self.ssh_connection)
        return KubeUpgradeShowOutput(output)

    def kube_upgrade_abort(self) -> KubeUpgradeShowOutput:
        """Executes the 'system kube-upgrade-abort' command.

        Returns:
            KubeUpgradeShowOutput: Parsed output of the command.
        """
        output = self.ssh_connection.send(source_openrc("system kube-upgrade-abort"))
        self.validate_success_return_code(self.ssh_connection)
        return KubeUpgradeShowOutput(output)

    def kube_upgrade_complete(self) -> KubeUpgradeShowOutput:
        """Executes the 'system kube-upgrade-complete' command.

        Returns:
            KubeUpgradeShowOutput: Parsed output of the command.
        """
        output = self.ssh_connection.send(source_openrc("system kube-upgrade-complete"))
        self.validate_success_return_code(self.ssh_connection)
        return KubeUpgradeShowOutput(output)

    def kube_upgrade_delete(self) -> None:
        """Executes the 'system kube-upgrade-delete' command.

        Raises:
            AssertionError: If SSH command fails.
        """
        self.ssh_connection.send(source_openrc("system kube-upgrade-delete"))
        self.validate_success_return_code(self.ssh_connection)
