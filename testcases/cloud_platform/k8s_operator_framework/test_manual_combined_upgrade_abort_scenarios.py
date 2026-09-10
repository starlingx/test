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

This module covers the Kubernetes-upgrade phase (kube-upgrade-start through
control-plane) plus 'software deploy start' and the subsequent 'system host-lock'.
Later deploy-phase abort points (deploy host onward) are covered separately.

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
# Upgrade sequence: stop-point constants
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
    up, so teardown never fails a test on an already-clean system.

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
        get_logger().log_teardown_step("Abort and delete software deploy if needed")
        try:
            USMKeywords(ssh_connection).software_deploy_abort()
        except (KeywordException, AssertionError):
            get_logger().log_info("No software deploy to abort")
        try:
            USMKeywords(ssh_connection).software_deploy_delete()
        except (KeywordException, AssertionError):
            get_logger().log_info("No software deploy to delete")

    def teardown_kube_upgrade() -> None:
        get_logger().log_teardown_step("Abort kubernetes upgrade if needed")
        try:
            KubeUpgradeKeywords(ssh_connection).kube_upgrade_abort()
        except (KeywordException, AssertionError):
            get_logger().log_info("No kubernetes upgrade to abort")
            return
        try:
            KubeUpgradeShowKeywords(ssh_connection).wait_for_kube_upgrade_state(KUBE_STATE_UPGRADE_ABORTED, timeout=300)
        except (KeywordException, AssertionError):
            get_logger().log_info("Timed out waiting for upgrade-aborted state")
        get_logger().log_teardown_step("Delete kubernetes upgrade if needed")
        try:
            KubeUpgradeKeywords(ssh_connection).kube_upgrade_delete()
        except (KeywordException, AssertionError):
            get_logger().log_info("No kubernetes upgrade to delete")

    request.addfinalizer(teardown_system_deploy)
    request.addfinalizer(teardown_software_deploy)
    request.addfinalizer(teardown_kube_upgrade)


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
    """Run 'software deploy start' and, for the host-lock stop point, lock the host.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        active_controller (str): Hostname of the active controller.
        target_platform_release (str): Target platform release to deploy.
        stop_step (int): Command to stop after (a STEP_* constant).
        timeout (int): Maximum wait time for state transitions.
    """
    get_logger().log_test_case_step(f"Send software deploy start for release {target_platform_release}")
    USMKeywords(ssh_connection).deploy_start(target_platform_release)
    _wait_deploy_start_done(ssh_connection, timeout)

    if stop_step == STEP_HOST_LOCK:
        # lock_host blocks until the host is locked (and raises otherwise).
        get_logger().log_test_case_step(f"Lock host {active_controller}")
        SystemHostLockKeywords(ssh_connection).lock_host(active_controller)


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
    # region the stop point falls in: the kube-phase rollback before any deploy command,
    # or the after-deploy-start rollback once 'software deploy start' has run.
    _run_kube_phase_until(ssh_connection, active_controller, target_kube_version, stop_step, wait_for_completion, timeout)

    if stop_step <= STEP_CONTROL_PLANE:
        _rollback_kube_phase(ssh_connection, timeout)
    else:
        _run_deploy_phase(ssh_connection, active_controller, target_platform_release, stop_step, timeout)
        _rollback_after_deploy_start(ssh_connection, active_controller, timeout)

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
