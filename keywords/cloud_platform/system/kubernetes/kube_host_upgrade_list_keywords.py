from typing import Sequence

from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.kubernetes.object.kube_host_upgrade_list_output import KubeHostUpgradeListOutput


class KubeHostUpgradeListKeywords(BaseKeyword):
    """Keywords for the 'system kube-host-upgrade-list' command."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def kube_host_upgrade_list(self) -> KubeHostUpgradeListOutput:
        """Executes the 'system kube-host-upgrade-list' command.

        Returns:
            KubeHostUpgradeListOutput: Parsed output of the command.
        """
        output = self.ssh_connection.send(source_openrc("system kube-host-upgrade-list"))
        self.validate_success_return_code(self.ssh_connection)
        return KubeHostUpgradeListOutput(output)

    def wait_for_host_upgrade_status(
        self,
        hostname: str,
        expected_status: str,
        timeout: int = 600,
        polling_sleep_time: int = 10,
        failure_statuses: Sequence[str] = (),
    ) -> None:
        """Waits for a host's upgrade status to reach the expected value.

        Polls 'system kube-host-upgrade-list' until the status of the
        specified host matches expected_status, or raises on timeout or
        fail-fast match.

        Args:
            hostname (str): Hostname to monitor.
            expected_status (str): Status to wait for.
            timeout (int): Maximum wait time in seconds.
            polling_sleep_time (int): Seconds between polls.
            failure_statuses (Sequence[str]): Statuses that trigger immediate failure.

        Raises:
            TimeoutError: If expected status is not reached within timeout.
            ValidationFailureError: If a failure status is observed.
        """

        def get_host_upgrade_status() -> str:
            return self.kube_host_upgrade_list().get_host_upgrade_by_hostname(hostname).get_status()

        validate_equals_with_retry(
            get_host_upgrade_status,
            expected_status,
            f"Host '{hostname}' upgrade status is '{expected_status}'",
            timeout,
            polling_sleep_time,
            failure_statuses,
        )

    def wait_for_host_control_plane_version(
        self,
        hostname: str,
        expected_version: str,
        timeout: int = 600,
        polling_sleep_time: int = 10,
    ) -> None:
        """Waits for a host's control plane version to reach the expected value.

        Polls 'system kube-host-upgrade-list' until the control plane version
        of the specified host matches expected_version, or raises on timeout.

        Args:
            hostname (str): Hostname to monitor.
            expected_version (str): Control plane version to wait for.
            timeout (int): Maximum wait time in seconds.
            polling_sleep_time (int): Seconds between polls.

        Raises:
            TimeoutError: If expected version is not reached within timeout.
        """

        def get_host_control_plane_version() -> str:
            return self.kube_host_upgrade_list().get_host_upgrade_by_hostname(hostname).get_control_plane_version()

        validate_equals_with_retry(
            get_host_control_plane_version,
            expected_version,
            f"Host '{hostname}' control plane version is '{expected_version}'",
            timeout,
            polling_sleep_time,
        )
