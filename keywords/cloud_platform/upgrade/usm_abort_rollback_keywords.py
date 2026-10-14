"""Keywords for USM abort/rollback via the software CLI.

Shared helpers for aborting a USM deployment and rolling every host back to the
previous release (N-1) using the ``software`` CLI (abort + optional
activate-rollback + per-host ``host-rollback`` with lock/unlock). Hosts are
rolled back in the reverse of deploy order (most recently deployed first):
workers -> storages -> active controller -> standby controller. The active
controller is swacted away first so it can be locked.

These are extracted from the post-reboot abort/rollback test so they can be
reused by other abort/rollback test cases.
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.upgrade.software_deploy_host_list_keywords import SoftwareDeployHostListKeywords
from keywords.cloud_platform.upgrade.software_deploy_show_keywords import SoftwareDeployShowKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords

from config.usm.objects.usm_config import USMConfig

# Timeout for a just-rolled-back-and-rebooted standby controller to become
# ready to accept a swact (unlocked/enabled/available).
STANDBY_READY_TIMEOUT = 1800

# ---------------------------------------------------------------------------
# Deploy states (software deploy show)
# ---------------------------------------------------------------------------
STATE_HOST_DONE = "deploy-host-done"
STATE_ACTIVATE = "deploy-activate"
STATE_ACTIVATE_DONE = "deploy-activate-done"
STATE_ACTIVATE_ROLLBACK_PENDING = "deploy-activate-rollback-pending"
STATE_ACTIVATE_ROLLBACK_DONE = "deploy-activate-rollback-done"
STATE_HOST_ROLLBACK = "deploy-host-rollback"
STATE_HOST_ROLLBACK_DONE = "deploy-host-rollback-done"

# Per-host states (software deploy host-list)
HOST_STATE_ROLLBACK_DEPLOYED = "deploy-host-rollback-deployed"
HOST_STATE_ROLLBACK_PENDING = "deploy-host-rollback-pending"

# Timeouts (seconds)
ABORT_STATE_TIMEOUT = 600
HOST_LIST_STATE_TIMEOUT = 1800
ACTIVATE_ROLLBACK_TIMEOUT = 1800


class UsmAbortRollbackKeywords(BaseKeyword):
    """Keywords for aborting a USM deploy and rolling hosts back via the software CLI."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get_current_deploy_state(self) -> str:
        """Get the current deploy state from 'software deploy show'.

        Returns:
            str: Current deploy state string.
        """
        deploy_show = SoftwareDeployShowKeywords(self.ssh_connection)
        return deploy_show.get_software_deploy_show().get_software_deploy_show().get_state()

    def get_host_state(self, hostname: str) -> str:
        """Get the deploy state of a single host from 'software deploy host-list'.

        Args:
            hostname (str): Host name to look up.

        Returns:
            str: State of the host in the deploy host-list (empty if not present).
        """
        host_list_kw = SoftwareDeployHostListKeywords(self.ssh_connection)
        return host_list_kw.get_software_deploy_host_list().get_state_by_host(hostname)

    def verify_release_is_deploying(self, release_id: str) -> None:
        """Verify the target release is in 'deploying' state.

        Args:
            release_id (str): The release ID to verify.
        """
        sw_list = SoftwareListKeywords(self.ssh_connection)
        state = sw_list.get_software_list().get_release_state_by_release_name(release_id)
        validate_equals(state, "deploying", f"Release {release_id} must be in deploying state for rollback")

    def verify_deploy_state(self, expected_state: str) -> None:
        """Assert the current deploy state matches the expected state.

        Args:
            expected_state (str): The expected deploy state.
        """
        validate_equals(self.get_current_deploy_state(), expected_state, f"System must be in {expected_state} state")

    # ------------------------------------------------------------------
    # Waits
    # ------------------------------------------------------------------

    def wait_for_host_state(self, hostname: str, expected_state: str, timeout: int = HOST_LIST_STATE_TIMEOUT) -> None:
        """Wait until a host reaches the expected deploy host-list state.

        Args:
            hostname (str): Host name to poll.
            expected_state (str): The state to wait for.
            timeout (int): Maximum time to wait, in seconds.
        """
        validate_equals_with_retry(
            function_to_execute=lambda: self.get_host_state(hostname),
            expected_value=expected_state,
            validation_description=f"{hostname} reached deploy state '{expected_state}'",
            timeout=timeout,
            polling_sleep_time=15,
        )

    def wait_for_deploy_state(self, expected_state: str, timeout: int = ABORT_STATE_TIMEOUT) -> None:
        """Wait until 'software deploy show' reports the expected deploy state.

        Args:
            expected_state (str): The deploy state to wait for.
            timeout (int): Maximum time to wait, in seconds.
        """
        validate_equals_with_retry(
            function_to_execute=lambda: self.get_current_deploy_state(),
            expected_value=expected_state,
            validation_description=f"Deploy state reached '{expected_state}'",
            timeout=timeout,
            polling_sleep_time=15,
        )

    # ------------------------------------------------------------------
    # Rollback flow
    # ------------------------------------------------------------------

    def get_host_rollback_order(self) -> list[str]:
        """Return hosts in rollback order: the reverse of deploy order.

        Hosts are deployed standby controller -> active controller -> storages
        (alphabetical) -> workers (alphabetical) (see
        USMKeywords.deploy_host_upgrade_order). 'software deploy host-rollback'
        enforces rolling back in the reverse order (most recently deployed
        first): workers (reverse alphabetical) -> storages (reverse
        alphabetical) -> active controller -> standby controller. This matters
        on a Standard system (storage/compute nodes present); rolling back in
        deploy order is rejected with "does not satisfy the right order of
        deployment".

        Returns:
            list[str]: Ordered host names to roll back.
        """
        usm_keywords = USMKeywords(self.ssh_connection)
        order: list[str] = []
        order.extend(sorted((h.get_host_name() for h in usm_keywords.computes_host_upgrade_list()), reverse=True))
        order.extend(sorted((h.get_host_name() for h in usm_keywords.storage_host_upgrade_list()), reverse=True))
        order.append(usm_keywords.active_controller_host_upgrade().get_host_name())
        standby = usm_keywords.standby_controller_host_upgrade()
        if standby is not None:
            order.append(standby.get_host_name())
        return order

    def wait_for_standby_controller_ready(self, timeout: int = STANDBY_READY_TIMEOUT) -> None:
        """Wait until a standby controller exists and is unlocked/enabled/available.

        A swact only succeeds when the standby controller is fully ready to
        become active. Right after a controller's host-rollback + unlock +
        reboot, the newly-rolled-back standby may still be coming up
        (locked/offline/degraded), so a swact issued too early is accepted but
        never completes the role flip (swact timeout). Gating the swact on the
        standby being unlocked/enabled/available avoids that.

        Args:
            timeout (int): Maximum time to wait, in seconds.
        """

        def standby_is_ready() -> bool:
            """Return True when a standby controller is unlocked/enabled/available."""
            try:
                standby = SystemHostListKeywords(self.ssh_connection).get_standby_controller()
            except Exception:
                return False
            if standby is None:
                return False
            return standby.get_administrative() == "unlocked" and standby.get_operational() == "enabled" and standby.get_availability() == "available"

        validate_equals_with_retry(
            function_to_execute=standby_is_ready,
            expected_value=True,
            validation_description="Standby controller is unlocked/enabled/available (ready to become active)",
            timeout=timeout,
            polling_sleep_time=15,
        )

    def rollback_host(self, usm_config: USMConfig, hostname: str) -> None:
        """Roll a single deployed host back to N-1: (swact if active) -> lock -> host-rollback -> unlock.

        The host was deployed and unlocked into release N; unlocking after the
        host-rollback reboots it back into N-1. The active controller cannot be
        locked, so it is swacted onto the standby first; this keyword's SSH
        connection is re-established against the new active controller afterwards.
        The swact is gated on the standby being ready and retried once, since a
        standby that just rebooted from a prior rollback may not be ready yet.

        Args:
            usm_config (USMConfig): USM configuration.
            hostname (str): Host to roll back.
        """
        usm_keywords = USMKeywords(self.ssh_connection)
        lock_keywords = SystemHostLockKeywords(self.ssh_connection)

        active_controller = usm_keywords.active_controller_host_upgrade()
        if active_controller.get_host_name() == hostname:
            get_logger().log_info(f"{hostname} is the active controller; swact before rollback")
            self.wait_for_standby_controller_ready()
            try:
                SystemHostSwactKeywords(self.ssh_connection).host_swact()
            except Exception as e:
                get_logger().log_warning(f"First swact attempt failed ({e}); waiting for standby to settle and retrying once")
                self.ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
                self.wait_for_standby_controller_ready()
                SystemHostSwactKeywords(self.ssh_connection).host_swact()
            self.ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
            usm_keywords = USMKeywords(self.ssh_connection)
            lock_keywords = SystemHostLockKeywords(self.ssh_connection)

        get_logger().log_info(f"Rolling back {hostname} (lock -> host-rollback -> unlock, reboots to N-1)")
        lock_keywords.lock_host(hostname)
        usm_keywords.software_deploy_host_rollback(hostname)
        self.wait_for_host_state(hostname, HOST_STATE_ROLLBACK_DEPLOYED)
        exclude_alarm_ids = usm_config.get_alarm_restrictions()
        lock_keywords.unlock_host(hostname, exclude_alarm_ids=exclude_alarm_ids)
        lock_keywords.wait_for_host_unlocked(hostname, exclude_alarm_ids=exclude_alarm_ids)
        get_logger().log_info(f"{hostname} rolled back and unlocked (booted into N-1)")

    def rollback_all_hosts(self, usm_config: USMConfig) -> None:
        """Roll back every host in order and wait for deploy-host-rollback-done.

        Args:
            usm_config (USMConfig): USM configuration.
        """
        host_order = self.get_host_rollback_order()
        get_logger().log_info(f"Host rollback order: {host_order}")

        for hostname in host_order:
            self.rollback_host(usm_config, hostname)

        get_logger().log_info("Waiting for deploy state to reach host-rollback-done")
        # Reconnect in case the active controller changed due to a swact.
        self.ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        self.wait_for_deploy_state(STATE_HOST_ROLLBACK_DONE, timeout=HOST_LIST_STATE_TIMEOUT)
