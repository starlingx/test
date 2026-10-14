"""Keywords for USM abort/rollback via the software CLI.

Shared helpers for aborting a USM deployment and rolling every host back to the
previous release (N-1) using the ``software`` CLI (abort + optional
activate-rollback + per-host ``host-rollback`` with lock/unlock), and for
advancing a deploy to a mixed pre-activate host state on a Standard system
(controllers / storages deployed, others pending, or one host mid deploy-host
'deploying') so an abort/rollback test can act on it.

Hosts are rolled back in the reverse of deploy order (most recently deployed
first): workers -> storages -> current standby controller -> current active
controller. (Controllers are deployed standby-first then active, and the
active controller swacts away to deploy, which flips roles -- so the
controller deployed last ends up as the current standby.) The active
controller cannot be locked while active, so it is swacted to standby first;
see swact_if_active_controller() / rollback_host().

These are shared by the abort/rollback test cases so the logic is reused
rather than duplicated.
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_list_contains
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.upgrade.software_deploy_host_list_keywords import SoftwareDeployHostListKeywords
from keywords.cloud_platform.upgrade.software_deploy_show_keywords import SoftwareDeployShowKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords

from config.usm.objects.usm_config import USMConfig

# ---------------------------------------------------------------------------
# Deploy states (software deploy show). Confirmed on real hardware: every
# state string reported by 'software deploy show' / 'software deploy
# host-list' carries the 'deploy-' / 'deploy-host-' prefix shown below, never
# the bare word.
# ---------------------------------------------------------------------------
STATE_START_DONE = "deploy-start-done"
STATE_HOST = "deploy-host"
STATE_HOST_DONE = "deploy-host-done"
STATE_ACTIVATE = "deploy-activate"
STATE_ACTIVATE_DONE = "deploy-activate-done"
STATE_ACTIVATE_ROLLBACK_PENDING = "deploy-activate-rollback-pending"
STATE_ACTIVATE_ROLLBACK_DONE = "deploy-activate-rollback-done"
STATE_HOST_ROLLBACK = "deploy-host-rollback"
STATE_HOST_ROLLBACK_DONE = "deploy-host-rollback-done"

# Per-host states (software deploy host-list)
HOST_STATE_PENDING = "deploy-host-pending"
HOST_STATE_DEPLOYED = "deploy-host-deployed"
HOST_STATE_DEPLOYING = "deploy-host-deploying"
HOST_STATE_ROLLBACK_DEPLOYED = "deploy-host-rollback-deployed"
HOST_STATE_ROLLBACK_PENDING = "deploy-host-rollback-pending"

# Timeouts (seconds)
ABORT_STATE_TIMEOUT = 600
HOST_LIST_STATE_TIMEOUT = 1800
ACTIVATE_ROLLBACK_TIMEOUT = 1800
STANDBY_READY_TIMEOUT = 1800
# Host deploy/rollback reboot hosts N<->N-1, so these run longer than a
# deploy-state-only wait.
DEPLOY_STATE_TIMEOUT = 1800
HOST_DEPLOY_TIMEOUT = 3600
HOST_ROLLBACK_TIMEOUT = 3600


class UsmAbortRollbackKeywords(BaseKeyword):
    """Keywords for USM deploy / abort / host-rollback flows via the software CLI."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection
        self.usm_keywords = USMKeywords(ssh_connection)
        self.lock_keywords = SystemHostLockKeywords(ssh_connection)

    # ------------------------------------------------------------------
    # State queries / verification
    # ------------------------------------------------------------------

    def get_current_deploy_state(self) -> str:
        """Get the current deploy state from 'software deploy show'.

        Returns:
            str: Current deploy state string.
        """
        deploy_show = SoftwareDeployShowKeywords(self.ssh_connection)
        return deploy_show.get_software_deploy_show().get_software_deploy_show().get_state()

    def has_active_deploy(self) -> bool:
        """Return whether a software deploy is currently in progress.

        Use to guard a teardown finalizer against rolling back a host after
        the main test body already finished and deleted the deploy.

        Returns:
            bool: True if 'software deploy show' reports an active deploy.
        """
        show = SoftwareDeployShowKeywords(self.ssh_connection).get_software_deploy_show().get_software_deploy_show()
        return show is not None

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

    def verify_host_state(self, host_name: str, expected_state: str) -> None:
        """Validate a single host's state in 'software deploy host-list'.

        Args:
            host_name (str): Host to check.
            expected_state (str): Expected host state (pending/deployed/deploying).
        """
        actual_state = self.get_host_state(host_name)
        validate_equals(actual_state, expected_state, f"Host '{host_name}' deploy state is '{expected_state}'")

    def verify_host_state_in(self, host_name: str, expected_states: list) -> None:
        """Validate a host's state in 'software deploy host-list' is one of several acceptable states.

        Use for a host left mid 'software deploy host' (locked, not
        unlocked): the 'deploying' state is transient and may already have
        completed to 'deployed' by the time this runs. Both are safe, since
        the host stays locked until this test's own rollback unlocks it.

        Args:
            host_name (str): Host to check.
            expected_states (list): Acceptable host states (e.g. [HOST_STATE_DEPLOYING, HOST_STATE_DEPLOYED]).
        """
        actual_state = self.get_host_state(host_name)
        validate_list_contains(actual_state, expected_states, f"Host '{host_name}' deploy state is one of {expected_states}")

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

    def wait_for_standby_controller_ready(self, timeout: int = STANDBY_READY_TIMEOUT) -> None:
        """Wait until a standby controller exists and is unlocked/enabled/available.

        A swact issued before the standby is fully ready is accepted but
        never completes.

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

    # ------------------------------------------------------------------
    # Preconditions / host discovery
    # ------------------------------------------------------------------

    def get_controllers(self) -> list:
        """Return controller hostnames in upgrade order (standby first, then active).

        Returns:
            list: Ordered controller hostnames.
        """
        controllers: list[str] = []
        standby = self.usm_keywords.standby_controller_host_upgrade()
        if standby is not None:
            controllers.append(standby.get_host_name())
        controllers.append(self.usm_keywords.active_controller_host_upgrade().get_host_name())
        return controllers

    # ------------------------------------------------------------------
    # Abort
    # ------------------------------------------------------------------

    def abort_deploy(self) -> None:
        """Issue 'software deploy abort' and verify the state becomes 'deploy-host-rollback'."""
        self.usm_keywords.software_deploy_abort()
        reached = self.usm_keywords.wait_for_deploy_state(STATE_HOST_ROLLBACK, timeout=DEPLOY_STATE_TIMEOUT)
        validate_equals(reached, True, f"Deploy state transitioned to '{STATE_HOST_ROLLBACK}' after abort")

    # ------------------------------------------------------------------
    # Rollback flow
    # ------------------------------------------------------------------

    def get_host_rollback_order(self) -> list[str]:
        """Return hosts in rollback order: the reverse of deploy order.

        Deploy order is standby controller -> active controller -> storages
        (alphabetical) -> workers (alphabetical). Deploying the active
        controller requires a swact first, which flips which physical host
        holds which role, so the controller deployed LAST ends up CURRENT
        STANDBY. Rollback order is therefore: workers (reverse alphabetical)
        -> storages (reverse alphabetical) -> current standby -> current
        active. Rolling back in the wrong order is rejected with "does not
        satisfy the right order of deployment".

        Returns:
            list[str]: Ordered host names to roll back.
        """
        usm_keywords = USMKeywords(self.ssh_connection)
        order: list[str] = []
        order.extend(sorted((h.get_host_name() for h in usm_keywords.computes_host_upgrade_list()), reverse=True))
        order.extend(sorted((h.get_host_name() for h in usm_keywords.storage_host_upgrade_list()), reverse=True))
        # Controllers are deployed standby-first, then active (which swacts away
        # first so it can be locked). The swact permanently flips roles, so the
        # controller deployed LAST ends up as the CURRENT STANDBY, and the one
        # deployed FIRST ends up as the CURRENT ACTIVE. Reverse-of-deploy-order
        # rollback therefore means: current standby first, then current active.
        standby = usm_keywords.standby_controller_host_upgrade()
        if standby is not None:
            order.append(standby.get_host_name())
        order.append(usm_keywords.active_controller_host_upgrade().get_host_name())
        return order

    def rollback_host(self, usm_config: USMConfig, hostname: str) -> None:
        """Roll a single deployed host back to N-1: (swact if active) -> lock -> host-rollback -> unlock.

        The active controller cannot be locked, so it is swacted to standby
        first, gated on the standby being ready and retried once.

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

    def rollback_host_in_progress(self, host_name: str) -> None:
        """Roll back a host that is mid deploy-host, then unlock it onto N-1.

        The host is already locked (it was left 'deploying'), so this issues
        host-rollback directly and then unlocks to reboot into N-1.

        Args:
            host_name (str): Host to roll back and unlock.
        """
        self.usm_keywords.software_deploy_host_rollback(host_name, lock_unlock=False)
        self.lock_keywords.unlock_host(host_name)

    def swact_if_active_controller(self, host_name: str) -> None:
        """Swact away from host_name if it is currently the active controller.

        The active controller cannot be locked, so host-rollback requires
        swacting to standby first. Re-establishes the SSH connection (and
        usm_keywords/lock_keywords) against the new active controller.

        Args:
            host_name (str): Host about to be rolled back.
        """
        active_controller = self.usm_keywords.active_controller_host_upgrade()
        if active_controller.get_host_name() != host_name:
            return

        get_logger().log_info(f"'{host_name}' is the active controller; swact before rollback")
        self.wait_for_standby_controller_ready()
        try:
            SystemHostSwactKeywords(self.ssh_connection).host_swact()
        except Exception as e:
            get_logger().log_warning(f"First swact attempt failed ({e}); waiting for standby to settle and retrying once")
            self.ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
            self.wait_for_standby_controller_ready()
            SystemHostSwactKeywords(self.ssh_connection).host_swact()

        self.ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        self.usm_keywords = USMKeywords(self.ssh_connection)
        self.lock_keywords = SystemHostLockKeywords(self.ssh_connection)

    def rollback_and_unlock_host(self, host_name: str, log_as_test_step: bool = False) -> None:
        """Roll a single deployed host back to N-1 (swact if active -> lock -> host-rollback -> unlock).

        The active controller cannot be locked, so it is swacted onto the
        standby first; see swact_if_active_controller().

        Args:
            host_name (str): Host to roll back.
            log_as_test_step (bool): If True, log as a test-case step (called
                from a real test step); if False (default), log as a
                teardown step (called from a finalizer/teardown context).
        """
        if log_as_test_step:
            get_logger().log_test_case_step(f"Rollback deployed host '{host_name}' to N-1")
        else:
            get_logger().log_teardown_step(f"Rollback host '{host_name}' to N-1")
        self.swact_if_active_controller(host_name)
        self.usm_keywords.software_deploy_host_rollback(host_name, lock_unlock=True)

    def finish_rollback_and_delete(self, deployed_hosts: list) -> None:
        """Roll back every deployed host, verify 'host-rollback-done', delete, no alarms.

        Hosts are rolled back in the EXACT order given; callers must pass
        them already in rollback order (most-recently-deployed first), the
        same convention as get_host_rollback_order(). Each host is swacted to
        standby first if currently active; see swact_if_active_controller().

        Args:
            deployed_hosts (list): Hostnames to roll back, already in rollback order.
        """
        for host_name in deployed_hosts:
            self.rollback_and_unlock_host(host_name, log_as_test_step=True)

        get_logger().log_test_case_step(f"Wait for '{STATE_HOST_ROLLBACK_DONE}' state")
        reached = self.usm_keywords.wait_for_deploy_state(STATE_HOST_ROLLBACK_DONE, timeout=DEPLOY_STATE_TIMEOUT)
        validate_equals(reached, True, f"Deploy state reached '{STATE_HOST_ROLLBACK_DONE}' after rolling back all hosts")

        get_logger().log_test_case_step("Delete the software deploy")
        self.usm_keywords.software_deploy_delete()

        get_logger().log_test_case_step("Verify no alarms remain")
        AlarmListKeywords(self.ssh_connection).wait_for_all_alarms_cleared()

    # ------------------------------------------------------------------
    # Cleanup / teardown
    # ------------------------------------------------------------------

    def cleanup_deploy(self) -> None:
        """Delete any lingering software deploy so the system is left clean.

        Idempotent: a missing deploy is logged and skipped.
        """
        get_logger().log_teardown_step("Delete software deploy if present")
        self.usm_keywords.software_deploy_delete(only_if_present=True)

    def rollback_remaining_hosts_if_needed(self, hosts: list) -> None:
        """Teardown-safe fallback: roll back only hosts not already rolled back.

        Use in an addfinalizer registered before the main test body runs,
        instead of calling rollback_and_unlock_host()/finish_rollback_and_delete()
        directly, since finalizers always run even if the main body already
        finished the rollback. Skips hosts already rolled back and no-ops if
        there is no active deploy left.

        Args:
            hosts (list): Hostnames to roll back, in rollback order, if needed.
        """
        get_logger().log_teardown_step("Roll back any still-pending host to N-1 if a deploy is still active")
        try:
            if not self.has_active_deploy():
                get_logger().log_info("No active deploy; main test body already rolled back and deleted it, skipping")
                return
            for host_name in hosts:
                state = self.get_host_state(host_name)
                if state == HOST_STATE_ROLLBACK_DEPLOYED:
                    get_logger().log_info(f"'{host_name}' already rolled back ('{state}'); skipping to avoid a redundant/unsafe re-rollback")
                    continue
                self.rollback_and_unlock_host(host_name)
        except Exception as e:
            get_logger().log_info(f"Rollback fallback skipped/failed (likely already rolled back by the test body): {e}")
