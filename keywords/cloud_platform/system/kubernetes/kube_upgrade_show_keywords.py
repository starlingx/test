from typing import Sequence

from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.kubernetes.object.kube_upgrade_show_output import KubeUpgradeShowOutput


class KubeUpgradeShowKeywords(BaseKeyword):
    """Keywords for the 'system kube-upgrade-show' command."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def kube_upgrade_show(self) -> KubeUpgradeShowOutput:
        """Executes the 'system kube-upgrade-show' command.

        Returns:
            KubeUpgradeShowOutput: Parsed output of the command.
        """
        output = self.ssh_connection.send(source_openrc("system kube-upgrade-show"))
        self.validate_success_return_code(self.ssh_connection)
        return KubeUpgradeShowOutput(output)

    def wait_for_kube_upgrade_state(
        self,
        expected_state: str,
        timeout: int = 600,
        polling_sleep_time: int = 10,
        failure_states: Sequence[str] = (),
    ) -> None:
        """Waits for the kubernetes upgrade to reach the expected state.

        Polls 'system kube-upgrade-show' until the upgrade state matches
        expected_state, or raises on timeout or fail-fast match.

        Args:
            expected_state (str): State to wait for (e.g. 'upgrade-complete').
            timeout (int): Maximum wait time in seconds.
            polling_sleep_time (int): Seconds between polls.
            failure_states (Sequence[str]): States that trigger immediate failure.

        Raises:
            TimeoutError: If expected state is not reached within timeout.
            ValidationFailureError: If a failure state is observed.
        """

        def get_kube_upgrade_state() -> str:
            return self.kube_upgrade_show().get_kube_upgrade_show_object().get_state()

        validate_equals_with_retry(
            get_kube_upgrade_state,
            expected_state,
            f"Kubernetes upgrade state is '{expected_state}'",
            timeout,
            polling_sleep_time,
            failure_states,
        )
