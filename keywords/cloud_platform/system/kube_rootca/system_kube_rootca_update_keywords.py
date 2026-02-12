import time

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.kube_rootca.objects.system_kube_rootca_host_update_list_output import SystemKubeRootcaHostUpdateListOutput
from keywords.cloud_platform.system.kube_rootca.objects.system_kube_rootca_update_show_output import SystemKubeRootcaUpdateShowOutput
from keywords.cloud_platform.system.kube_rootca.objects.system_kube_rootca_update_vertical_output import SystemKubeRootcaUpdateVerticalOutput


class SystemKubeRootcaUpdateKeywords(BaseKeyword):
    """Keywords for Kubernetes Root CA certificate update operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize kube rootca update keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        self.ssh_connection = ssh_connection
        self.system_host_list = SystemHostListKeywords(ssh_connection)

    def kube_rootca_update_start(self, force: bool = False) -> SystemKubeRootcaUpdateVerticalOutput:
        """Start kube rootca update.

        Args:
            force (bool): Force start without confirmation.

        Returns:
            SystemKubeRootcaUpdateVerticalOutput: Update status output.
        """
        cmd = "system kube-rootca-update-start"
        if force:
            cmd += " --force"
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return SystemKubeRootcaUpdateVerticalOutput(output)

    def kube_rootca_update_generate_cert(self, expiry_date: str, subject: str) -> SystemKubeRootcaUpdateVerticalOutput:
        """Generate new rootca certificate.

        Args:
            expiry_date (str): Certificate expiry date (YYYY-MM-DD).
            subject (str): Certificate subject string.

        Returns:
            SystemKubeRootcaUpdateVerticalOutput: Certificate generation output.
        """
        cmd = f'system kube-rootca-update-generate-cert --expiry-date="{expiry_date}" --subject="{subject}"'
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return SystemKubeRootcaUpdateVerticalOutput(output)

    def kube_rootca_update_show(self) -> SystemKubeRootcaUpdateShowOutput:
        """Show kube rootca update status.

        Returns:
            SystemKubeRootcaUpdateShowOutput: Update status output.
        """
        cmd = "system kube-rootca-update-show"
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return SystemKubeRootcaUpdateShowOutput(output)

    def kube_rootca_host_update(self, hostname: str, phase: str) -> SystemKubeRootcaUpdateVerticalOutput:
        """Update host with specified phase.

        Args:
            hostname (str): Host to update.
            phase (str): Update phase (trust-both-cas, update-certs, trust-new-ca).

        Returns:
            SystemKubeRootcaUpdateVerticalOutput: Update status output.
        """
        cmd = f"system kube-rootca-host-update {hostname} --phase={phase}"
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return SystemKubeRootcaUpdateVerticalOutput(output)

    def kube_rootca_host_update_list(self) -> SystemKubeRootcaHostUpdateListOutput:
        """List kube rootca host update status.

        Returns:
            SystemKubeRootcaHostUpdateListOutput: Host update list output.
        """
        cmd = "system kube-rootca-host-update-list"
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return SystemKubeRootcaHostUpdateListOutput(output)

    def kube_rootca_pods_update(self, phase: str) -> SystemKubeRootcaUpdateVerticalOutput:
        """Update pods with specified phase.

        Args:
            phase (str): Update phase (trust-both-cas, trust-new-ca).

        Returns:
            SystemKubeRootcaUpdateVerticalOutput: Update status output.
        """
        cmd = f"system kube-rootca-pods-update --phase={phase}"
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return SystemKubeRootcaUpdateVerticalOutput(output)

    def kube_rootca_update_complete(self) -> SystemKubeRootcaUpdateVerticalOutput:
        """Complete kube rootca update.

        Returns:
            SystemKubeRootcaUpdateVerticalOutput: Update status output.
        """
        cmd = "system kube-rootca-update-complete"
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return SystemKubeRootcaUpdateVerticalOutput(output)

    def wait_for_update_state(self, expected_state: str, timeout: int = 300) -> bool:
        """Wait for update to reach expected state.

        Args:
            expected_state (str): Expected state.
            timeout (int): Timeout in seconds.

        Returns:
            bool: True if state reached, False if timeout.
        """
        timeout_time = time.time() + timeout
        while time.time() < timeout_time:
            update_output = self.kube_rootca_update_show()
            current_state = update_output.get_kube_rootca_update().get_state()
            if current_state == expected_state:
                return True
            time.sleep(2)
        return False

    def wait_for_host_update_state(self, hostname: str, expected_state: str, timeout: int = 600) -> bool:
        """Wait for host to reach expected update state.

        Args:
            hostname (str): Hostname to check.
            expected_state (str): Expected state.
            timeout (int): Timeout in seconds.

        Returns:
            bool: True if state reached, False if timeout.
        """
        timeout_time = time.time() + timeout
        while time.time() < timeout_time:
            try:
                host_list = self.kube_rootca_host_update_list()
                host_update = host_list.get_host_update(hostname)
                if host_update and host_update.get_state() == expected_state:
                    return True
            except Exception:
                pass
            time.sleep(2)
        return False
