"""
Validate combined (Platform + Kubernetes) upgrade abort scenarios.

A combined upgrade (initiated via 'software system-deploy init') is a single
linear sequence of commands. Each test drives that sequence forward up to a
chosen cut-off command, aborts, and verifies the system returns to its original
state. The abort/rollback procedure depends only on which region of the sequence
the cut-off falls in.

The sequence is driven by _run_combined_upgrade_until: each test names the command
to stop after (a STEP_* constant); the driver runs every earlier command, runs the
stop command, then applies the rollback procedure valid for that region.

This module covers the full combined-upgrade sequence: the Kubernetes-upgrade phase
(kube-upgrade-start through control-plane), the platform-deploy phase ('software
deploy start', 'system host-lock', 'software deploy host', 'system host-unlock',
'software deploy activate', 'software deploy complete'), and the Kubernetes-completion
phase ('system kube-upgrade-complete', 'system kube-post-application-update', and
'system kube-upgrade-delete'). Each test aborts at one stop point and the driver
applies the rollback procedure valid for that region.

Prerequisites:
    - Lab must be in a state where a combined upgrade can be started
      (release uploaded and available, system healthy).
    - Runs on simplex lab.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.kubernetes.etcd_keywords import EtcdKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_keywords import KubeHostUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_list_keywords import KubeHostUpgradeListKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_keywords import KubeUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_show_keywords import KubeUpgradeShowKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from keywords.cloud_platform.upgrade.software_deploy_show_keywords import SoftwareDeployShowKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords

# =============================================================================
# Constants
# =============================================================================

# --- Kube-upgrade completion states (kube-upgrade-show 'state' column) ---

KUBE_STATE_DOWNLOADED_IMAGES = "downloaded-images"
KUBE_STATE_PRE_UPDATED_APPS = "pre-updated-apps"
KUBE_STATE_UPGRADED_NETWORKING = "upgraded-networking"
KUBE_STATE_UPGRADED_STORAGE = "upgraded-storage"
KUBE_STATE_UPGRADED_FIRST_MASTER = "upgraded-first-master"
KUBE_STATE_UPGRADE_ABORTED = "upgrade-aborted"

# --- Platform deploy-phase states (software deploy show 'State' column) ---

DEPLOY_STATE_START_DONE = "deploy-start-done"
DEPLOY_STATE_HOST_DONE = "deploy-host-done"
DEPLOY_STATE_ACTIVATE_DONE = "deploy-activate-done"
DEPLOY_STATE_COMPLETED = "deploy-completed"

# --- Kube-upgrade states reached during the platform deploy / completion phase ---

KUBE_STATE_UPGRADE_COMPLETE = "upgrade-complete"
# NOTE: the CLI 'kube-upgrade-show' may display 'kube-post-application-updated',
# but the automation framework (and every other test) waits on 'post-updated-apps'.
KUBE_STATE_POST_UPDATED_APPS = "post-updated-apps"


# =============================================================================
# Helpers: version record / verify
# =============================================================================


def _get_control_plane_version(ssh_connection: SSHConnection, hostname: str) -> str:
    """Get the current control-plane version for a host.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        hostname (str): Hostname to query the control-plane version for.

    Returns:
        str: The control-plane version string (e.g. 'v1.31.9').
    """
    kube_host_upgrade_list_keywords = KubeHostUpgradeListKeywords(ssh_connection)
    return kube_host_upgrade_list_keywords.kube_host_upgrade_list().get_host_upgrade_by_hostname(hostname).get_control_plane_version()


def _get_etcd_version(ssh_connection: SSHConnection) -> str:
    """Get the current etcd version.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        str: The etcd version string.
    """
    etcd_keywords = EtcdKeywords(ssh_connection)
    return etcd_keywords.get_etcd_version()


def _verify_kube_and_etcd_versions_rolled_back(hostname: str, original_control_plane_version: str, original_etcd_version: str) -> None:
    """Verify control-plane (kubernetes) and etcd versions rolled back to their originals.

    Establishes a fresh SSH connection to the active controller (the connection may
    have been reset by the abort/rollback) and validates both versions.

    Args:
        hostname (str): Hostname to query the control-plane version for.
        original_control_plane_version (str): Control-plane version recorded before upgrade.
        original_etcd_version (str): Etcd version recorded before upgrade.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify control-plane version rolled back to original")
    rollback_version = _get_control_plane_version(ssh_connection, hostname)
    get_logger().log_info(f"Control-plane version after abort: {rollback_version}")
    validate_equals(rollback_version, original_control_plane_version, "Control-plane version rolled back to original")

    get_logger().log_test_case_step("Verify etcd version rolled back to original")
    rollback_etcd_version = _get_etcd_version(ssh_connection)
    get_logger().log_info(f"Etcd version after abort: {rollback_etcd_version}")
    validate_equals(rollback_etcd_version, original_etcd_version, "Etcd version rolled back to original")


# =============================================================================
# Upgrade sequence: context + stop-point constants
# =============================================================================


# Stop points a test can abort at, in sequence order. A test names the command to
# stop after; the driver runs every earlier command, runs the stop command, then
# applies the rollback procedure valid for that point.
STEP_KUBE_UPGRADE_START = 0
STEP_DOWNLOAD_IMAGES = 1
STEP_PRE_APPLICATION_UPDATE = 2
STEP_UPGRADE_NETWORKING = 3
STEP_UPGRADE_STORAGE = 4
STEP_CONTROL_PLANE = 5
STEP_DEPLOY_START = 6
STEP_HOST_LOCK = 7
STEP_DEPLOY_HOST = 8
STEP_HOST_UNLOCK = 9
STEP_DEPLOY_ACTIVATE = 10
STEP_DEPLOY_COMPLETE = 11
STEP_KUBE_UPGRADE_COMPLETE = 12
STEP_KUBE_POST_APPLICATION_UPDATE = 13
STEP_KUBE_UPGRADE_DELETE = 14

# Deploy-phase stop points (deploy host onward) run the full platform deploy, which
# takes longer than the kube-only phase, so they use a longer state-transition timeout.
DEPLOY_PHASE_TIMEOUT = 1200

# =============================================================================
# Helpers: waits + rollback procedures
# =============================================================================


def _wait_control_plane_reached_target(ssh_connection: SSHConnection, active_controller: str, target_kube_version: str, timeout: int) -> None:
    """Repeat the control-plane upgrade until the target Kubernetes version is reached.

    A single 'kube-host-upgrade control-plane' advances the host by only one minor
    version. Before 'software deploy start' the control-plane must already be at the
    target Kubernetes version. The caller sends the first control-plane upgrade; this
    then waits for 'upgraded-first-master' and repeats the upgrade one minor version at
    a time until the host's control-plane version equals the target.

    Two conditions end the loop other than success: the stall guard raises if an
    upgrade ran but the version did not advance, and the platform itself caps the
    number of consecutive control-plane upgrades and rejects a further attempt with an
    error (surfaced by the send inside the loop) — so no separate iteration cap is kept.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        active_controller (str): Hostname of the active controller.
        target_kube_version (str): Target Kubernetes version for the kube upgrade.
        timeout (int): Maximum wait time for state transitions.
    """
    kube_host_upgrade_keywords = KubeHostUpgradeKeywords(ssh_connection)
    kube_host_upgrade_list_keywords = KubeHostUpgradeListKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    completed_state = KUBE_STATE_UPGRADED_FIRST_MASTER
    failure_states = ["upgrading-first-master-failed"]

    previous_version = None
    while True:
        get_logger().log_test_case_step(f"Wait for '{completed_state}' kube upgrade state")
        kube_upgrade_show_keywords.wait_for_kube_upgrade_state(completed_state, timeout=timeout, failure_states=failure_states)

        current_version = kube_host_upgrade_list_keywords.kube_host_upgrade_list().get_host_upgrade_by_hostname(active_controller).get_control_plane_version()
        if current_version == target_kube_version:
            get_logger().log_info(f"Control-plane reached target {target_kube_version}")
            break

        # Guard against a stall: the upgrade ran but the version did not advance.
        if previous_version is not None and current_version == previous_version:
            raise KeywordException(f"Control-plane version did not advance past {current_version} (target {target_kube_version})")
        previous_version = current_version

        get_logger().log_test_case_step(f"Upgrade control-plane; current={current_version}, target={target_kube_version}")
        kube_host_upgrade_keywords.kube_host_upgrade_control_plane(active_controller)

    get_logger().log_test_case_step(f"Verify control-plane version reached target {target_kube_version}")
    validate_equals(
        kube_host_upgrade_list_keywords.kube_host_upgrade_list().get_host_upgrade_by_hostname(active_controller).get_control_plane_version(),
        target_kube_version,
        "Control-plane version reached target Kubernetes version",
    )


def _wait_deploy_start_done(ssh_connection: SSHConnection, timeout: int) -> None:
    """Wait for the software deploy to reach 'deploy-start-done'.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        timeout (int): Maximum wait time for state transitions.
    """
    get_logger().log_test_case_step(f"Wait for '{DEPLOY_STATE_START_DONE}' deploy state")
    validate_equals(USMKeywords(ssh_connection).wait_for_deploy_state(DEPLOY_STATE_START_DONE, timeout=timeout), True, f"Deploy reached '{DEPLOY_STATE_START_DONE}' state")


def _rollback_kube_phase(ssh_connection: SSHConnection, timeout: int) -> None:
    """Abort a combined upgrade during the Kubernetes-upgrade phase.

    Valid before any 'software deploy' command: abort the kube upgrade, wait for
    'upgrade-aborted', delete the kube upgrade, and delete the system deploy.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        timeout (int): Maximum wait time for state transitions.
    """
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    usm_keywords = USMKeywords(ssh_connection)

    get_logger().log_test_case_step("Abort the Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_abort()

    get_logger().log_test_case_step("Wait for upgrade-aborted state")
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(KUBE_STATE_UPGRADE_ABORTED, timeout=timeout)

    get_logger().log_test_case_step("Delete the Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_delete()

    get_logger().log_test_case_step("Delete the system deploy")
    usm_keywords.system_deploy_delete()


def _rollback_after_deploy_start(ssh_connection: SSHConnection, active_controller: str, timeout: int) -> None:
    """Abort and roll back a combined upgrade after 'software deploy start'.

    Valid after 'software deploy start' and before 'software deploy host' (also
    applies after 'system host-lock', which is why it unlocks the host first).

    Steps:
        - Unlock the host if it is locked
        - software deploy delete
        - system kube-upgrade-abort
        - Wait for the kube upgrade to reach 'upgrade-aborted'
        - system kube-upgrade-delete
        - software system-deploy delete

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        active_controller (str): Hostname of the active controller.
        timeout (int): Maximum wait time for state transitions.
    """
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    usm_keywords = USMKeywords(ssh_connection)
    system_host_lock_keywords = SystemHostLockKeywords(ssh_connection)

    get_logger().log_test_case_step("Unlock the host if it is locked")
    if system_host_lock_keywords.is_host_locked(active_controller):
        system_host_lock_keywords.unlock_host(active_controller)

    get_logger().log_test_case_step("Delete the software deploy")
    usm_keywords.software_deploy_delete()

    get_logger().log_test_case_step("Abort the Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_abort()

    get_logger().log_test_case_step("Wait for upgrade-aborted state")
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(KUBE_STATE_UPGRADE_ABORTED, timeout=timeout)

    get_logger().log_test_case_step("Delete the Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_delete()

    get_logger().log_test_case_step("Delete the system deploy")
    usm_keywords.system_deploy_delete()


def _rollback_after_deploy_host(ssh_connection: SSHConnection, active_controller: str, timeout: int) -> None:
    """Abort and roll back a combined upgrade after 'software deploy host'.

    Valid after 'software deploy host' and before 'software deploy activate' (also
    applies after the subsequent 'system host-unlock').

    Steps:
        - software deploy abort
        - system host-lock, software deploy host-rollback, system host-unlock
        - software deploy delete
        - software system-deploy delete

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        active_controller (str): Hostname of the active controller.
        timeout (int): Maximum wait time for state transitions.
    """
    usm_keywords = USMKeywords(ssh_connection)
    system_host_lock_keywords = SystemHostLockKeywords(ssh_connection)

    get_logger().log_test_case_step("Abort the software deploy")
    usm_keywords.software_deploy_abort()

    get_logger().log_test_case_step(f"Roll back {active_controller} (lock, host-rollback, unlock)")
    if not system_host_lock_keywords.is_host_locked(active_controller):
        system_host_lock_keywords.lock_host(active_controller)
    usm_keywords.software_deploy_host_rollback(active_controller)
    system_host_lock_keywords.unlock_host(active_controller)

    get_logger().log_test_case_step("Delete the software deploy")
    usm_keywords.software_deploy_delete()

    get_logger().log_test_case_step("Delete the system deploy")
    usm_keywords.system_deploy_delete()


def _rollback_after_deploy_activate(ssh_connection: SSHConnection, active_controller: str, timeout: int) -> None:
    """Abort and roll back a combined upgrade after 'software deploy activate'.

    Valid once 'software deploy activate' has run (also applies after 'software deploy
    complete', 'system kube-upgrade-complete', 'system kube-post-application-update',
    and 'system kube-upgrade-delete', since all of those keep the deploy in the
    activated region).

    Steps:
        - software deploy abort
        - software deploy activate-rollback
        - system host-lock, software deploy host-rollback, system host-unlock
        - software deploy delete
        - software system-deploy delete

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        active_controller (str): Hostname of the active controller.
        timeout (int): Maximum wait time for state transitions.
    """
    usm_keywords = USMKeywords(ssh_connection)
    system_host_lock_keywords = SystemHostLockKeywords(ssh_connection)

    get_logger().log_test_case_step("Abort the software deploy")
    usm_keywords.software_deploy_abort()

    get_logger().log_test_case_step("Perform the activate-rollback")
    usm_keywords.software_deploy_activate_rollback()

    get_logger().log_test_case_step(f"Roll back {active_controller} (lock, host-rollback, unlock)")
    if not system_host_lock_keywords.is_host_locked(active_controller):
        system_host_lock_keywords.lock_host(active_controller)
    usm_keywords.software_deploy_host_rollback(active_controller)
    system_host_lock_keywords.unlock_host(active_controller)

    get_logger().log_test_case_step("Delete the software deploy")
    usm_keywords.software_deploy_delete()

    get_logger().log_test_case_step("Delete the system deploy")
    usm_keywords.system_deploy_delete()


# =============================================================================
# Driver: run the sequence to a stop point and abort
# =============================================================================


def _resolve_target_platform_release(ssh_connection: SSHConnection) -> str:
    """Resolve the target platform release for the upgrade.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        str: The target platform release name (first release in 'available' state).
    """
    get_logger().log_setup_step("Get available software release")
    software_list = SoftwareListKeywords(ssh_connection).get_software_list()
    available_release = software_list.get_release_name_by_state("available")
    validate_not_equals(available_release, [], "At least one release in 'available' state must exist")
    target_platform_release = available_release[0]
    get_logger().log_info(f"Target platform release: {target_platform_release}")
    return target_platform_release


def _resolve_target_kube_version(ssh_connection: SSHConnection) -> str:
    """Resolve the target Kubernetes version for the upgrade.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        str: The target Kubernetes version resolved from the available versions.
    """
    get_logger().log_setup_step("Resolve target Kubernetes version")
    available_kube_versions = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list().get_version_by_state("available")
    validate_not_equals(available_kube_versions, [], "At least one Kubernetes version in 'available' state must exist")
    target_kube_version = ConfigurationManager.get_kubernetes_upgrade_config().resolve_target_version(available_kube_versions)
    get_logger().log_info(f"Target Kubernetes version: {target_kube_version}")
    return target_kube_version


def _register_combined_upgrade_teardowns(request: FixtureRequest, ssh_connection: SSHConnection, timeout: int) -> None:
    """Register independent teardown finalizers for the combined upgrade (LIFO order).

    Each finalizer is best-effort: it logs and continues if there is nothing to clean
    up, so teardown never fails a test on an already-clean system. The software-deploy
    finalizer inspects the current 'software deploy show' state and applies the matching
    rollback, so a deploy left in any region (started, host-deployed, or activated) is
    fully unwound rather than leaking a locked host and in-progress deploy/kube upgrade.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown registration.
        ssh_connection (SSHConnection): SSH connection to the active controller.
        timeout (int): Maximum wait time for state transitions.
    """

    def teardown_system_deploy() -> None:
        get_logger().log_teardown_step("Delete system deploy if needed")
        try:
            USMKeywords(ssh_connection).system_deploy_delete()
        except (KeywordException, AssertionError):
            get_logger().log_info("No system deploy to delete")

    def teardown_software_deploy() -> None:
        get_logger().log_teardown_step("Roll back and delete software deploy if needed")
        try:
            deploy = SoftwareDeployShowKeywords(ssh_connection).get_software_deploy_show().get_software_deploy_show()
        except (KeywordException, AssertionError):
            deploy = None
        if deploy is None:
            get_logger().log_info("No software deploy to roll back")
            return
        state = deploy.get_state()
        get_logger().log_info(f"Software deploy present in state '{state}'")
        try:
            # 'activate'/'completed' states need activate-rollback first; 'host'/'start'
            # states need the host-rollback path. 'deploy-start*' (before any host deploy)
            # only needs a plain delete. The after-deploy-* helpers end by deleting both
            # the software deploy and the system deploy.
            if "activate" in state or "completed" in state:
                _rollback_after_deploy_activate(ssh_connection, active_controller_name(), timeout)
            elif "host" in state:
                _rollback_after_deploy_host(ssh_connection, active_controller_name(), timeout)
            else:
                _rollback_after_deploy_start(ssh_connection, active_controller_name(), timeout)
        except (KeywordException, AssertionError) as e:
            get_logger().log_info(f"Software deploy rollback encountered an issue during teardown: {e}")

    def teardown_kube_upgrade() -> None:
        get_logger().log_teardown_step("Abort kubernetes upgrade if needed")
        try:
            KubeUpgradeKeywords(ssh_connection).kube_upgrade_abort()
            KubeUpgradeShowKeywords(ssh_connection).wait_for_kube_upgrade_state(KUBE_STATE_UPGRADE_ABORTED, timeout=300)
        except (KeywordException, AssertionError):
            # A standalone abort is invalid once a deploy is/was in progress (the deploy
            # rollback already unwinds kube); fall through and still attempt the delete so
            # the kube-upgrade entity and its alarm (900.007) are cleared.
            get_logger().log_info("Kubernetes upgrade abort not applicable, attempting delete")
        get_logger().log_teardown_step("Delete kubernetes upgrade if needed")
        try:
            KubeUpgradeKeywords(ssh_connection).kube_upgrade_delete()
        except (KeywordException, AssertionError):
            get_logger().log_info("No kubernetes upgrade to delete")

    def active_controller_name() -> str:
        """Return the active controller hostname using a fresh query.

        Returns:
            str: The active controller hostname.
        """
        return SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    # LIFO: register so the software-deploy rollback runs BEFORE the kube-upgrade
    # cleanup. Once a deploy is in progress the kube upgrade cannot be aborted on its
    # own; the software-deploy rollback must unwind the combined deploy first, after
    # which the kube-upgrade entity can be deleted. The system-deploy delete runs last
    # as a final safety net (the rollback helpers already delete it).
    request.addfinalizer(teardown_system_deploy)
    request.addfinalizer(teardown_kube_upgrade)
    request.addfinalizer(teardown_software_deploy)


def _run_kube_command(ssh_connection: SSHConnection, step: int, wait: bool, timeout: int) -> None:
    """Send a single kube-phase command and, when wait is True, wait for its completed state.

    The post-start Kubernetes-upgrade commands form a uniform mapping of STEP_* constant
    -> (step_log, bound command, completed_state, failure_states); each command is a
    zero-arg bound keyword method. kube-upgrade-start and control-plane are handled
    separately as they do not fit the "one command, wait for one state" shape.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        step (int): Kube-phase command to run (a STEP_* constant).
        wait (bool): If True, wait for the command's completed state after sending it.
        timeout (int): Maximum wait time for state transitions.
    """
    kube = KubeUpgradeKeywords(ssh_connection)
    kube_phase = {
        STEP_DOWNLOAD_IMAGES: ("Send kube-upgrade-download-images", kube.kube_upgrade_download_images, KUBE_STATE_DOWNLOADED_IMAGES, ["downloading-images-failed"]),
        STEP_PRE_APPLICATION_UPDATE: ("Send kube-pre-application-update", kube.kube_pre_application_update, KUBE_STATE_PRE_UPDATED_APPS, ["pre-updating-apps-failed"]),
        STEP_UPGRADE_NETWORKING: ("Send kube-upgrade-networking", kube.kube_upgrade_networking, KUBE_STATE_UPGRADED_NETWORKING, ["upgrading-networking-failed"]),
        STEP_UPGRADE_STORAGE: ("Send kube-upgrade-storage", kube.kube_upgrade_storage, KUBE_STATE_UPGRADED_STORAGE, ["upgrading-storage-failed"]),
    }
    step_log, command, completed_state, failure_states = kube_phase[step]
    get_logger().log_test_case_step(step_log)
    command()
    if wait and completed_state is not None:
        get_logger().log_test_case_step(f"Wait for '{completed_state}' kube upgrade state")
        KubeUpgradeShowKeywords(ssh_connection).wait_for_kube_upgrade_state(completed_state, timeout=timeout, failure_states=failure_states)


def _run_control_plane(ssh_connection: SSHConnection, active_controller: str, target_kube_version: str, wait: bool, timeout: int) -> None:
    """Send the control-plane upgrade; when wait is True, repeat until the target is reached.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        active_controller (str): Hostname of the active controller.
        target_kube_version (str): Target Kubernetes version for the kube upgrade.
        wait (bool): If True, repeat the control-plane upgrade until the target is reached.
        timeout (int): Maximum wait time for state transitions.
    """
    get_logger().log_test_case_step("Send kube-host-upgrade control-plane")
    KubeHostUpgradeKeywords(ssh_connection).kube_host_upgrade_control_plane(active_controller)
    if wait:
        _wait_control_plane_reached_target(ssh_connection, active_controller, target_kube_version, timeout)


def _run_kube_phase_until(ssh_connection: SSHConnection, active_controller: str, target_kube_version: str, stop_step: int, wait_for_completion: bool, timeout: int) -> None:
    """Run the Kubernetes-upgrade phase up to and including the stop command.

    kube-upgrade-start always runs first (it has no wait). Every command before the stop
    is waited to completion; the stop command's wait depends on wait_for_completion. When
    stop_step is beyond the control-plane (deploy phase), the whole kube phase including
    control-plane repeat-to-target is run to completion.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        active_controller (str): Hostname of the active controller.
        target_kube_version (str): Target Kubernetes version for the kube upgrade.
        stop_step (int): Command to stop after (a STEP_* constant).
        wait_for_completion (bool): If True, wait for the stop command to complete.
        timeout (int): Maximum wait time for state transitions.
    """
    get_logger().log_test_case_step("Send kube-upgrade-start")
    KubeUpgradeKeywords(ssh_connection).kube_upgrade_start(target_kube_version)

    # Deploy phase requires the control-plane already at target: run the full kube phase.
    effective_stop = stop_step if stop_step <= STEP_CONTROL_PLANE else STEP_CONTROL_PLANE

    for step in range(STEP_DOWNLOAD_IMAGES, min(effective_stop, STEP_CONTROL_PLANE)):
        _run_kube_command(ssh_connection, step, wait=True, timeout=timeout)

    # kube-upgrade-start has already run. For STEP_KUBE_UPGRADE_START there is nothing
    # more to send; otherwise send the stop command (control-plane is special). In the
    # deploy phase the control-plane is always waited to target.
    if effective_stop == STEP_KUBE_UPGRADE_START:
        return
    if effective_stop < STEP_CONTROL_PLANE:
        _run_kube_command(ssh_connection, effective_stop, wait=wait_for_completion, timeout=timeout)
    else:
        wait_control_plane = wait_for_completion or stop_step > STEP_CONTROL_PLANE
        _run_control_plane(ssh_connection, active_controller, target_kube_version, wait=wait_control_plane, timeout=timeout)


def _run_deploy_phase(ssh_connection: SSHConnection, active_controller: str, target_platform_release: str, stop_step: int, timeout: int) -> None:
    """Run the platform-deploy and Kubernetes-completion sequence up to the stop point.

    Drives the linear sequence that follows the control-plane upgrade, stopping after
    the command named by ``stop_step``:
    deploy start -> host-lock -> deploy host -> host-unlock -> deploy activate ->
    deploy complete -> kube-upgrade-complete -> kube-post-application-update ->
    kube-upgrade-delete. Each state-changing command is waited to its completed state
    before the next is sent.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        active_controller (str): Hostname of the active controller.
        target_platform_release (str): Target platform release to deploy.
        stop_step (int): Command to stop after (a STEP_* constant >= STEP_DEPLOY_START).
        timeout (int): Maximum wait time for state transitions.
    """
    usm_keywords = USMKeywords(ssh_connection)
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    system_host_lock_keywords = SystemHostLockKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Send software deploy start for release {target_platform_release}")
    usm_keywords.deploy_start(target_platform_release)
    _wait_deploy_start_done(ssh_connection, timeout)
    if stop_step == STEP_DEPLOY_START:
        return

    get_logger().log_test_case_step(f"Lock host {active_controller}")
    system_host_lock_keywords.lock_host(active_controller)
    if stop_step == STEP_HOST_LOCK:
        return

    get_logger().log_test_case_step(f"Deploy the software release to {active_controller}")
    usm_keywords.software_deploy_host(active_controller)
    get_logger().log_test_case_step(f"Wait for '{DEPLOY_STATE_HOST_DONE}' deploy state")
    validate_equals(usm_keywords.wait_for_deploy_state(DEPLOY_STATE_HOST_DONE, timeout=timeout), True, f"Deploy reached '{DEPLOY_STATE_HOST_DONE}' state")
    if stop_step == STEP_DEPLOY_HOST:
        return

    get_logger().log_test_case_step(f"Unlock host {active_controller}")
    system_host_lock_keywords.unlock_host(active_controller)
    if stop_step == STEP_HOST_UNLOCK:
        return

    get_logger().log_test_case_step("Activate the software deploy")
    usm_keywords.software_deploy_activate()
    get_logger().log_test_case_step(f"Wait for '{DEPLOY_STATE_ACTIVATE_DONE}' deploy state")
    validate_equals(usm_keywords.wait_for_deploy_state(DEPLOY_STATE_ACTIVATE_DONE, timeout=timeout), True, f"Deploy reached '{DEPLOY_STATE_ACTIVATE_DONE}' state")
    if stop_step == STEP_DEPLOY_ACTIVATE:
        return

    get_logger().log_test_case_step("Complete the software deploy")
    usm_keywords.software_deploy_complete()
    get_logger().log_test_case_step(f"Wait for '{DEPLOY_STATE_COMPLETED}' deploy state")
    validate_equals(usm_keywords.wait_for_deploy_state(DEPLOY_STATE_COMPLETED, timeout=timeout), True, f"Deploy reached '{DEPLOY_STATE_COMPLETED}' state")
    if stop_step == STEP_DEPLOY_COMPLETE:
        return

    get_logger().log_test_case_step("Complete the Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_complete()
    get_logger().log_test_case_step(f"Wait for '{KUBE_STATE_UPGRADE_COMPLETE}' kube upgrade state")
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(KUBE_STATE_UPGRADE_COMPLETE, timeout=timeout)
    if stop_step == STEP_KUBE_UPGRADE_COMPLETE:
        return

    get_logger().log_test_case_step("Run kube-post-application-update")
    kube_upgrade_keywords.kube_post_application_update()
    get_logger().log_test_case_step(f"Wait for '{KUBE_STATE_POST_UPDATED_APPS}' kube upgrade state")
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(KUBE_STATE_POST_UPDATED_APPS, timeout=timeout)
    if stop_step == STEP_KUBE_POST_APPLICATION_UPDATE:
        return

    get_logger().log_test_case_step("Delete the Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_delete()


def _run_combined_upgrade_until(
    request: FixtureRequest,
    stop_step: int,
    wait_for_completion: bool = True,
    timeout: int = 600,
) -> None:
    """Drive the combined upgrade to a stop point, then apply the region's rollback.

    The combined upgrade is one linear sequence of commands. This runs every command
    before ``stop_step`` to completion, then runs the stop command. When
    ``wait_for_completion`` is True the stop command is waited to its completed state
    (the "abort after <step> completed" scenarios); when False only the command is sent
    and the wait is skipped (the "abort immediately after sending <step>" scenarios).
    Finally the rollback procedure valid for the stop point's region is applied.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown registration.
        stop_step (int): Command to stop after (a STEP_* constant).
        wait_for_completion (bool): If True, wait for the stop command to complete before
            aborting; if False, abort immediately after sending the stop command.
        timeout (int): Maximum wait time for state transitions.
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    target_platform_release = _resolve_target_platform_release(ssh_connection)
    target_kube_version = _resolve_target_kube_version(ssh_connection)

    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()
    get_logger().log_info(f"Active controller: {active_controller}")

    _register_combined_upgrade_teardowns(request, ssh_connection, timeout)

    get_logger().log_test_case_step(f"Initialize combined upgrade: system-deploy init {target_platform_release} --kube-upgrade {target_kube_version}")
    USMKeywords(ssh_connection).system_deploy_init(target_platform_release, kube_upgrade=target_kube_version)

    # Run the kube phase up to the stop point, then apply the rollback valid for the
    # region the stop point falls in. The reference procedure defines three deploy-phase
    # rollbacks keyed on how far the deploy progressed:
    #   - before any deploy command            -> kube-phase rollback
    #   - after deploy start, before deploy host-> after-deploy-start rollback
    #   - after deploy host, before activate    -> after-deploy-host rollback
    #   - after deploy activate (and beyond)    -> after-deploy-activate rollback
    _run_kube_phase_until(ssh_connection, active_controller, target_kube_version, stop_step, wait_for_completion, timeout)

    if stop_step <= STEP_CONTROL_PLANE:
        _rollback_kube_phase(ssh_connection, timeout)
        AlarmListKeywords(ssh_connection).wait_for_all_alarms_cleared()
        return

    _run_deploy_phase(ssh_connection, active_controller, target_platform_release, stop_step, timeout)

    if stop_step <= STEP_HOST_LOCK:
        _rollback_after_deploy_start(ssh_connection, active_controller, timeout)
    elif stop_step <= STEP_HOST_UNLOCK:
        _rollback_after_deploy_host(ssh_connection, active_controller, timeout)
    else:
        _rollback_after_deploy_activate(ssh_connection, active_controller, timeout)

    AlarmListKeywords(ssh_connection).wait_for_all_alarms_cleared()


# =============================================================================
# Tests: Abort after system kube-upgrade-start
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_kube_upgrade_start(request: FixtureRequest) -> None:
    """Test aborting a combined upgrade immediately after kube-upgrade-start.

    Initializes a combined upgrade via 'software system-deploy init', starts the
    Kubernetes upgrade, and aborts right away without sending any further upgrade
    command. The kube-phase rollback deletes the kube upgrade and the system deploy.
    Restricted to simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and resolve target platform release and kube version
        - Initialize combined upgrade via system-deploy init
        - Start the Kubernetes upgrade
        - Abort the Kubernetes upgrade and wait for upgrade-aborted state
        - Delete the Kubernetes upgrade and the system deploy
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_combined_upgrade_until(request, STEP_KUBE_UPGRADE_START)


# =============================================================================
# Tests: Abort after system kube-upgrade-download-images
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_immediately_after_download_images(request: FixtureRequest) -> None:
    """Test aborting immediately after sending kube-upgrade-download-images.

    Initializes a combined upgrade, starts the Kubernetes upgrade, sends
    kube-upgrade-download-images and aborts immediately without waiting for the
    download to complete. The kube-phase rollback deletes the kube upgrade and the
    system deploy. Restricted to simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and resolve target platform release and kube version
        - Initialize combined upgrade via system-deploy init
        - Start the Kubernetes upgrade
        - Send kube-upgrade-download-images (do not wait for completion)
        - Abort the Kubernetes upgrade and wait for upgrade-aborted state
        - Delete the Kubernetes upgrade and the system deploy
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_combined_upgrade_until(request, STEP_DOWNLOAD_IMAGES, wait_for_completion=False)


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_download_images_completed(request: FixtureRequest) -> None:
    """Test aborting after kube-upgrade-download-images has completed.

    Initializes a combined upgrade, starts the Kubernetes upgrade, sends
    kube-upgrade-download-images and waits for the downloaded-images state before
    aborting. The kube-phase rollback deletes the kube upgrade and the system deploy.
    Restricted to simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and resolve target platform release and kube version
        - Initialize combined upgrade via system-deploy init
        - Start the Kubernetes upgrade
        - Send kube-upgrade-download-images and wait for the downloaded-images state
        - Abort the Kubernetes upgrade and wait for upgrade-aborted state
        - Delete the Kubernetes upgrade and the system deploy
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_combined_upgrade_until(request, STEP_DOWNLOAD_IMAGES, wait_for_completion=True)


# =============================================================================
# Tests: Abort after system kube-pre-application-update
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_immediately_after_pre_application_update(request: FixtureRequest) -> None:
    """Test aborting immediately after sending kube-pre-application-update.

    Drives the combined upgrade through download-images, then sends
    kube-pre-application-update and aborts immediately without waiting for it to
    complete. The kube-phase rollback deletes the kube upgrade and the system deploy.
    Restricted to simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and resolve target platform release and kube version
        - Initialize combined upgrade via system-deploy init
        - Start the Kubernetes upgrade
        - Download images and wait for completion
        - Send kube-pre-application-update (do not wait for completion)
        - Abort the Kubernetes upgrade and wait for upgrade-aborted state
        - Delete the Kubernetes upgrade and the system deploy
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_combined_upgrade_until(request, STEP_PRE_APPLICATION_UPDATE, wait_for_completion=False)


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_pre_application_update_completed(request: FixtureRequest) -> None:
    """Test aborting after kube-pre-application-update has completed.

    Drives the combined upgrade through download-images, then sends
    kube-pre-application-update and waits for the pre-updated-apps state before
    aborting. The kube-phase rollback deletes the kube upgrade and the system deploy.
    Restricted to simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and resolve target platform release and kube version
        - Initialize combined upgrade via system-deploy init
        - Start the Kubernetes upgrade
        - Download images and wait for completion
        - Send kube-pre-application-update and wait for the pre-updated-apps state
        - Abort the Kubernetes upgrade and wait for upgrade-aborted state
        - Delete the Kubernetes upgrade and the system deploy
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_combined_upgrade_until(request, STEP_PRE_APPLICATION_UPDATE, wait_for_completion=True)


# =============================================================================
# Tests: Abort after system kube-upgrade-networking
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_immediately_after_upgrade_networking(request: FixtureRequest) -> None:
    """Test aborting immediately after sending kube-upgrade-networking.

    Drives the combined upgrade through pre-application-update, then sends
    kube-upgrade-networking and aborts immediately without waiting for it to complete.
    The kube-phase rollback deletes the kube upgrade and the system deploy. Restricted
    to simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and resolve target platform release and kube version
        - Initialize combined upgrade via system-deploy init
        - Start the Kubernetes upgrade
        - Download images and wait for completion
        - Run pre-application-update and wait for completion
        - Send kube-upgrade-networking (do not wait for completion)
        - Abort the Kubernetes upgrade and wait for upgrade-aborted state
        - Delete the Kubernetes upgrade and the system deploy
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_combined_upgrade_until(request, STEP_UPGRADE_NETWORKING, wait_for_completion=False)


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_upgrade_networking_completed(request: FixtureRequest) -> None:
    """Test aborting after kube-upgrade-networking has completed.

    Drives the combined upgrade through pre-application-update, then sends
    kube-upgrade-networking and waits for the upgraded-networking state before
    aborting. The kube-phase rollback deletes the kube upgrade and the system deploy.
    Restricted to simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and resolve target platform release and kube version
        - Initialize combined upgrade via system-deploy init
        - Start the Kubernetes upgrade
        - Download images and wait for completion
        - Run pre-application-update and wait for completion
        - Send kube-upgrade-networking and wait for the upgraded-networking state
        - Abort the Kubernetes upgrade and wait for upgrade-aborted state
        - Delete the Kubernetes upgrade and the system deploy
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_combined_upgrade_until(request, STEP_UPGRADE_NETWORKING, wait_for_completion=True)


# =============================================================================
# Tests: Abort after system kube-upgrade-storage
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_immediately_after_upgrade_storage(request: FixtureRequest) -> None:
    """Test aborting immediately after sending kube-upgrade-storage.

    Drives the combined upgrade through networking, then sends kube-upgrade-storage
    and aborts immediately without waiting for it to complete. The kube-phase rollback
    deletes the kube upgrade and the system deploy. Restricted to simplex labs via the
    lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and resolve target platform release and kube version
        - Initialize combined upgrade via system-deploy init
        - Start the Kubernetes upgrade
        - Download images and wait for completion
        - Run pre-application-update and wait for completion
        - Upgrade networking and wait for completion
        - Send kube-upgrade-storage (do not wait for completion)
        - Abort the Kubernetes upgrade and wait for upgrade-aborted state
        - Delete the Kubernetes upgrade and the system deploy
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_combined_upgrade_until(request, STEP_UPGRADE_STORAGE, wait_for_completion=False)


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_upgrade_storage_completed(request: FixtureRequest) -> None:
    """Test aborting after kube-upgrade-storage has completed.

    Drives the combined upgrade through networking, then sends kube-upgrade-storage
    and waits for the upgraded-storage state before aborting. The kube-phase rollback
    deletes the kube upgrade and the system deploy. Restricted to simplex labs via the
    lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and resolve target platform release and kube version
        - Initialize combined upgrade via system-deploy init
        - Start the Kubernetes upgrade
        - Download images and wait for completion
        - Run pre-application-update and wait for completion
        - Upgrade networking and wait for completion
        - Send kube-upgrade-storage and wait for the upgraded-storage state
        - Abort the Kubernetes upgrade and wait for upgrade-aborted state
        - Delete the Kubernetes upgrade and the system deploy
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_combined_upgrade_until(request, STEP_UPGRADE_STORAGE, wait_for_completion=True)


# =============================================================================
# Tests: Abort after system kube-host-upgrade control-plane
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_immediately_after_host_upgrade_control_plane(request: FixtureRequest) -> None:
    """Test aborting immediately after sending kube-host-upgrade control-plane.

    Drives the combined upgrade through storage, then sends the first
    kube-host-upgrade control-plane and aborts immediately without waiting for the
    control-plane to reach the target version. The kube-phase rollback deletes the
    kube upgrade and the system deploy. Restricted to simplex labs via the
    lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and resolve target platform release and kube version
        - Initialize combined upgrade via system-deploy init
        - Start the Kubernetes upgrade
        - Download images and wait for completion
        - Run pre-application-update and wait for completion
        - Upgrade networking and wait for completion
        - Upgrade storage and wait for completion
        - Send kube-host-upgrade control-plane (do not wait for completion)
        - Abort the Kubernetes upgrade and wait for upgrade-aborted state
        - Delete the Kubernetes upgrade and the system deploy
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_combined_upgrade_until(request, STEP_CONTROL_PLANE, wait_for_completion=False)


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_host_upgrade_control_plane_completed(request: FixtureRequest) -> None:
    """Test aborting after kube-host-upgrade control-plane completed, with rollback verification.

    Records the control-plane and etcd versions, drives the combined upgrade through
    storage, upgrades the control-plane to the target Kubernetes version, then aborts.
    After the kube-phase rollback it verifies both the control-plane and etcd versions
    rolled back to their originals. Restricted to simplex labs via the lab_is_simplex
    marker.

    Test Steps:
        - Establish SSH connection and record original control-plane and etcd versions
        - Initialize combined upgrade via system-deploy init
        - Start the Kubernetes upgrade
        - Download images and wait for completion
        - Run pre-application-update and wait for completion
        - Upgrade networking and wait for completion
        - Upgrade storage and wait for completion
        - Upgrade control-plane and wait until the target Kubernetes version is reached
        - Abort the Kubernetes upgrade and wait for upgrade-aborted state
        - Delete the Kubernetes upgrade and the system deploy
        - Wait for all alarms to clear
        - Verify the control-plane and etcd versions rolled back to their originals

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_setup_step("Record control-plane version before upgrade")
    original_control_plane_version = _get_control_plane_version(ssh_connection, active_controller)
    get_logger().log_info(f"Control-plane version before upgrade: {original_control_plane_version}")

    get_logger().log_setup_step("Record etcd version before upgrade")
    original_etcd_version = _get_etcd_version(ssh_connection)
    get_logger().log_info(f"Etcd version before upgrade: {original_etcd_version}")

    _run_combined_upgrade_until(request, STEP_CONTROL_PLANE, wait_for_completion=True)

    _verify_kube_and_etcd_versions_rolled_back(active_controller, original_control_plane_version, original_etcd_version)


# =============================================================================
# Tests: Abort after software deploy start
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_deploy_start(request: FixtureRequest) -> None:
    """Test aborting a combined upgrade after 'software deploy start' completes.

    Records the control-plane and etcd versions, drives the combined upgrade through
    the full Kubernetes phase (control-plane at target), runs 'software deploy start'
    and waits for deploy-start-done, then applies the after-deploy-start rollback.
    Afterwards it verifies both versions rolled back to their originals. Restricted to
    simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and record original control-plane and etcd versions
        - Run the combined upgrade through the control-plane (reaching the target version)
        - Send software deploy start and wait for deploy-start-done
        - Unlock the host if locked
        - Delete the software deploy
        - Abort the Kubernetes upgrade and wait for upgrade-aborted state
        - Delete the Kubernetes upgrade and the system deploy
        - Wait for all alarms to clear
        - Verify the control-plane and etcd versions rolled back to their originals

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_setup_step("Record control-plane version before upgrade")
    original_control_plane_version = _get_control_plane_version(ssh_connection, active_controller)
    get_logger().log_info(f"Control-plane version before upgrade: {original_control_plane_version}")

    get_logger().log_setup_step("Record etcd version before upgrade")
    original_etcd_version = _get_etcd_version(ssh_connection)
    get_logger().log_info(f"Etcd version before upgrade: {original_etcd_version}")

    _run_combined_upgrade_until(request, STEP_DEPLOY_START, wait_for_completion=True)

    _verify_kube_and_etcd_versions_rolled_back(active_controller, original_control_plane_version, original_etcd_version)


# =============================================================================
# Tests: Abort after system host-lock (before software deploy host)
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_host_lock(request: FixtureRequest) -> None:
    """Test aborting a combined upgrade after 'system host-lock' completes.

    Records the control-plane and etcd versions, drives the combined upgrade through
    'software deploy start', then locks the host. Because the host is locked after
    deploy-start-done but before 'software deploy host', the after-deploy-start
    rollback applies (it unlocks the host first). Afterwards it verifies both versions
    rolled back to their originals. Restricted to simplex labs via the lab_is_simplex
    marker.

    Test Steps:
        - Establish SSH connection and record original control-plane and etcd versions
        - Run the combined upgrade through the control-plane (reaching the target version)
        - Send software deploy start and wait for deploy-start-done
        - Lock the host and wait for it to become locked
        - Unlock the host (part of the after-deploy-start rollback)
        - Delete the software deploy
        - Abort the Kubernetes upgrade and wait for upgrade-aborted state
        - Delete the Kubernetes upgrade and the system deploy
        - Wait for all alarms to clear
        - Verify the control-plane and etcd versions rolled back to their originals

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_setup_step("Record control-plane version before upgrade")
    original_control_plane_version = _get_control_plane_version(ssh_connection, active_controller)
    get_logger().log_info(f"Control-plane version before upgrade: {original_control_plane_version}")

    get_logger().log_setup_step("Record etcd version before upgrade")
    original_etcd_version = _get_etcd_version(ssh_connection)
    get_logger().log_info(f"Etcd version before upgrade: {original_etcd_version}")

    _run_combined_upgrade_until(request, STEP_HOST_LOCK, wait_for_completion=True)

    _verify_kube_and_etcd_versions_rolled_back(active_controller, original_control_plane_version, original_etcd_version)


# =============================================================================
# Tests: Abort after software deploy host
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_deploy_host(request: FixtureRequest) -> None:
    """Test aborting a combined upgrade after 'software deploy host' completes.

    Drives the combined upgrade through the control-plane, software deploy start,
    host-lock, and 'software deploy host'. Since 'software deploy activate' has not
    run, the after-deploy-host rollback applies (deploy abort, host-lock,
    host-rollback, host-unlock, deploy delete, system-deploy delete), then verifies
    both versions rolled back to their originals. Restricted to simplex labs via the
    lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and record original control-plane and etcd versions
        - Run the combined upgrade through the control-plane (reaching the target version)
        - Send software deploy start and wait for deploy-start-done
        - Lock the host
        - Send software deploy host and wait for deploy-host-done
        - Abort the software deploy
        - Lock the host, roll back the deploy host, and unlock the host
        - Delete the software deploy and the system deploy
        - Wait for all alarms to clear
        - Verify the control-plane and etcd versions rolled back to their originals

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_setup_step("Record control-plane version before upgrade")
    original_control_plane_version = _get_control_plane_version(ssh_connection, active_controller)
    get_logger().log_info(f"Control-plane version before upgrade: {original_control_plane_version}")

    get_logger().log_setup_step("Record etcd version before upgrade")
    original_etcd_version = _get_etcd_version(ssh_connection)
    get_logger().log_info(f"Etcd version before upgrade: {original_etcd_version}")

    _run_combined_upgrade_until(request, STEP_DEPLOY_HOST, wait_for_completion=True, timeout=DEPLOY_PHASE_TIMEOUT)

    _verify_kube_and_etcd_versions_rolled_back(active_controller, original_control_plane_version, original_etcd_version)


# =============================================================================
# Tests: Abort after system host-unlock (after deploy host, before activate)
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_host_unlock(request: FixtureRequest) -> None:
    """Test aborting a combined upgrade after 'system host-unlock' completes.

    Drives the combined upgrade through the control-plane, software deploy start,
    host-lock, 'software deploy host', and host-unlock. Since 'software deploy
    activate' has not run, the after-deploy-host rollback applies, then verifies both
    versions rolled back to their originals. Restricted to simplex labs via the
    lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and record original control-plane and etcd versions
        - Run the combined upgrade through the control-plane (reaching the target version)
        - Send software deploy start and wait for deploy-start-done
        - Lock the host
        - Send software deploy host and wait for deploy-host-done
        - Unlock the host
        - Abort the software deploy
        - Lock the host, roll back the deploy host, and unlock the host
        - Delete the software deploy and the system deploy
        - Wait for all alarms to clear
        - Verify the control-plane and etcd versions rolled back to their originals

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_setup_step("Record control-plane version before upgrade")
    original_control_plane_version = _get_control_plane_version(ssh_connection, active_controller)
    get_logger().log_info(f"Control-plane version before upgrade: {original_control_plane_version}")

    get_logger().log_setup_step("Record etcd version before upgrade")
    original_etcd_version = _get_etcd_version(ssh_connection)
    get_logger().log_info(f"Etcd version before upgrade: {original_etcd_version}")

    _run_combined_upgrade_until(request, STEP_HOST_UNLOCK, wait_for_completion=True, timeout=DEPLOY_PHASE_TIMEOUT)

    _verify_kube_and_etcd_versions_rolled_back(active_controller, original_control_plane_version, original_etcd_version)


# =============================================================================
# Tests: Abort after software deploy activate
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_deploy_activate(request: FixtureRequest) -> None:
    """Test aborting a combined upgrade after 'software deploy activate' completes.

    Drives the combined upgrade through the control-plane and the full deploy-host
    sequence, then runs 'software deploy activate'. The after-deploy-activate rollback
    applies (deploy abort, activate-rollback, host-lock, host-rollback, host-unlock,
    deploy delete, system-deploy delete), then verifies both versions rolled back to
    their originals. Restricted to simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and record original control-plane and etcd versions
        - Run the combined upgrade through the control-plane (reaching the target version)
        - Run software deploy start, host-lock, deploy host, and host-unlock
        - Send software deploy activate and wait for deploy-activate-done
        - Abort the software deploy
        - Roll back the deploy activate
        - Lock the host, roll back the deploy host, and unlock the host
        - Delete the software deploy and the system deploy
        - Wait for all alarms to clear
        - Verify the control-plane and etcd versions rolled back to their originals

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_setup_step("Record control-plane version before upgrade")
    original_control_plane_version = _get_control_plane_version(ssh_connection, active_controller)
    get_logger().log_info(f"Control-plane version before upgrade: {original_control_plane_version}")

    get_logger().log_setup_step("Record etcd version before upgrade")
    original_etcd_version = _get_etcd_version(ssh_connection)
    get_logger().log_info(f"Etcd version before upgrade: {original_etcd_version}")

    _run_combined_upgrade_until(request, STEP_DEPLOY_ACTIVATE, wait_for_completion=True, timeout=DEPLOY_PHASE_TIMEOUT)

    _verify_kube_and_etcd_versions_rolled_back(active_controller, original_control_plane_version, original_etcd_version)


# =============================================================================
# Tests: Abort after software deploy complete
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_deploy_complete(request: FixtureRequest) -> None:
    """Test aborting a combined upgrade after 'software deploy complete' finishes.

    Drives the combined upgrade through the control-plane, the full deploy-host
    sequence, and 'software deploy activate', then runs 'software deploy complete'.
    The after-deploy-activate rollback applies, then verifies both versions rolled
    back to their originals. Restricted to simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and record original control-plane and etcd versions
        - Run the combined upgrade through the control-plane (reaching the target version)
        - Run software deploy start, host-lock, deploy host, host-unlock, and activate
        - Send software deploy complete and wait for deploy-completed
        - Abort the software deploy
        - Roll back the deploy activate
        - Lock the host, roll back the deploy host, and unlock the host
        - Delete the software deploy and the system deploy
        - Wait for all alarms to clear
        - Verify the control-plane and etcd versions rolled back to their originals

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_setup_step("Record control-plane version before upgrade")
    original_control_plane_version = _get_control_plane_version(ssh_connection, active_controller)
    get_logger().log_info(f"Control-plane version before upgrade: {original_control_plane_version}")

    get_logger().log_setup_step("Record etcd version before upgrade")
    original_etcd_version = _get_etcd_version(ssh_connection)
    get_logger().log_info(f"Etcd version before upgrade: {original_etcd_version}")

    _run_combined_upgrade_until(request, STEP_DEPLOY_COMPLETE, wait_for_completion=True, timeout=DEPLOY_PHASE_TIMEOUT)

    _verify_kube_and_etcd_versions_rolled_back(active_controller, original_control_plane_version, original_etcd_version)


# =============================================================================
# Tests: Abort after system kube-upgrade-complete
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_kube_upgrade_complete(request: FixtureRequest) -> None:
    """Test aborting a combined upgrade after 'system kube-upgrade-complete' finishes.

    Drives the combined upgrade through the control-plane, the full deploy sequence
    (activate and complete), then completes the Kubernetes upgrade to 'upgrade-complete'.
    The after-deploy-activate rollback applies, then verifies both versions rolled back
    to their originals. Restricted to simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and record original control-plane and etcd versions
        - Run the combined upgrade through the control-plane (reaching the target version)
        - Run software deploy start, host-lock, deploy host, host-unlock, activate, and complete
        - Complete the Kubernetes upgrade and wait for 'upgrade-complete'
        - Abort the software deploy
        - Roll back the deploy activate
        - Lock the host, roll back the deploy host, and unlock the host
        - Delete the software deploy and the system deploy
        - Wait for all alarms to clear
        - Verify the control-plane and etcd versions rolled back to their originals

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_setup_step("Record control-plane version before upgrade")
    original_control_plane_version = _get_control_plane_version(ssh_connection, active_controller)
    get_logger().log_info(f"Control-plane version before upgrade: {original_control_plane_version}")

    get_logger().log_setup_step("Record etcd version before upgrade")
    original_etcd_version = _get_etcd_version(ssh_connection)
    get_logger().log_info(f"Etcd version before upgrade: {original_etcd_version}")

    _run_combined_upgrade_until(request, STEP_KUBE_UPGRADE_COMPLETE, wait_for_completion=True, timeout=DEPLOY_PHASE_TIMEOUT)

    _verify_kube_and_etcd_versions_rolled_back(active_controller, original_control_plane_version, original_etcd_version)


# =============================================================================
# Tests: Abort after system kube-post-application-update
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_kube_post_application_update(request: FixtureRequest) -> None:
    """Test aborting a combined upgrade after 'system kube-post-application-update'.

    Drives the combined upgrade through the control-plane, the full deploy sequence,
    the Kubernetes upgrade completion, and the post-application-update to
    'post-updated-apps'. The after-deploy-activate rollback applies, then verifies both
    versions rolled back to their originals. Restricted to simplex labs via the
    lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and record original control-plane and etcd versions
        - Run the combined upgrade through the control-plane (reaching the target version)
        - Run software deploy start, host-lock, deploy host, host-unlock, activate, and complete
        - Complete the Kubernetes upgrade and wait for 'upgrade-complete'
        - Run kube-post-application-update and wait for 'post-updated-apps'
        - Abort the software deploy
        - Roll back the deploy activate
        - Lock the host, roll back the deploy host, and unlock the host
        - Delete the software deploy and the system deploy
        - Wait for all alarms to clear
        - Verify the control-plane and etcd versions rolled back to their originals

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_setup_step("Record control-plane version before upgrade")
    original_control_plane_version = _get_control_plane_version(ssh_connection, active_controller)
    get_logger().log_info(f"Control-plane version before upgrade: {original_control_plane_version}")

    get_logger().log_setup_step("Record etcd version before upgrade")
    original_etcd_version = _get_etcd_version(ssh_connection)
    get_logger().log_info(f"Etcd version before upgrade: {original_etcd_version}")

    _run_combined_upgrade_until(request, STEP_KUBE_POST_APPLICATION_UPDATE, wait_for_completion=True, timeout=DEPLOY_PHASE_TIMEOUT)

    _verify_kube_and_etcd_versions_rolled_back(active_controller, original_control_plane_version, original_etcd_version)


# =============================================================================
# Tests: Abort after system kube-upgrade-delete
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_kube_upgrade_delete(request: FixtureRequest) -> None:
    """Test aborting a combined upgrade after 'system kube-upgrade-delete'.

    Drives the combined upgrade through the control-plane, the full deploy sequence,
    the Kubernetes upgrade completion, the post-application-update, and the deletion of
    the kube-upgrade entity. Only the platform deploy remains, so the
    after-deploy-activate rollback applies (the kube-upgrade abort/delete teardown steps
    become no-ops since the entity is already gone), then verifies both versions rolled
    back to their originals. Restricted to simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Establish SSH connection and record original control-plane and etcd versions
        - Run the combined upgrade through the control-plane (reaching the target version)
        - Run software deploy start, host-lock, deploy host, host-unlock, activate, and complete
        - Complete the Kubernetes upgrade and wait for 'upgrade-complete'
        - Run kube-post-application-update and wait for 'post-updated-apps'
        - Delete the Kubernetes upgrade
        - Abort the software deploy
        - Roll back the deploy activate
        - Lock the host, roll back the deploy host, and unlock the host
        - Delete the software deploy and the system deploy
        - Wait for all alarms to clear
        - Verify the control-plane and etcd versions rolled back to their originals

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_setup_step("Record control-plane version before upgrade")
    original_control_plane_version = _get_control_plane_version(ssh_connection, active_controller)
    get_logger().log_info(f"Control-plane version before upgrade: {original_control_plane_version}")

    get_logger().log_setup_step("Record etcd version before upgrade")
    original_etcd_version = _get_etcd_version(ssh_connection)
    get_logger().log_info(f"Etcd version before upgrade: {original_etcd_version}")

    _run_combined_upgrade_until(request, STEP_KUBE_UPGRADE_DELETE, wait_for_completion=True, timeout=DEPLOY_PHASE_TIMEOUT)

    _verify_kube_and_etcd_versions_rolled_back(active_controller, original_control_plane_version, original_etcd_version)
