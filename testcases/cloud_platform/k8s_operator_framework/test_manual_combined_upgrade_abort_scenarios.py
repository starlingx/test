"""
Validate combined (Platform + Kubernetes) upgrade abort scenarios.

These tests exercise aborting a kube upgrade at various stages during a
combined upgrade initiated via 'software system-deploy init'. Each test
issues the abort command either immediately after a step command is sent
or after the step has completed, then verifies the system reaches the
'upgrade-aborted' state. Cleanup removes both the kube-upgrade and the
system-deploy entities.

Prerequisites:
    - Lab must be in a state where a combined upgrade can be started
      (release uploaded and available, system healthy).
    - Runs on simplex lab.
"""

from typing import Optional

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.kubernetes.etcd_keywords import EtcdKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_keywords import KubeHostUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_list_keywords import KubeHostUpgradeListKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_keywords import KubeUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_show_keywords import KubeUpgradeShowKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords

# =============================================================================
# Step definitions: (completed_state, failure_states)
# =============================================================================

STEP_DOWNLOAD_IMAGES = "download-images"
STEP_PRE_APPLICATION_UPDATE = "pre-application-update"
STEP_UPGRADE_NETWORKING = "upgrade-networking"
STEP_UPGRADE_STORAGE = "upgrade-storage"
STEP_CONTROL_PLANE = "control-plane"

_STEP_TABLE = {
    STEP_DOWNLOAD_IMAGES: ("downloaded-images", ["downloading-images-failed"]),
    STEP_PRE_APPLICATION_UPDATE: ("pre-updated-apps", ["pre-updating-apps-failed"]),
    STEP_UPGRADE_NETWORKING: ("upgraded-networking", ["upgrading-networking-failed"]),
    STEP_UPGRADE_STORAGE: ("upgraded-storage", ["upgrading-storage-failed"]),
    STEP_CONTROL_PLANE: ("upgraded-first-master", ["upgrading-first-master-failed"]),
}

_STEP_ORDER = [
    STEP_DOWNLOAD_IMAGES,
    STEP_PRE_APPLICATION_UPDATE,
    STEP_UPGRADE_NETWORKING,
    STEP_UPGRADE_STORAGE,
    STEP_CONTROL_PLANE,
]


def _highest_kube_version(versions: list) -> str:
    """Return the highest Kubernetes version using semantic comparison.

    Args:
        versions (list): List of version strings (e.g. ['v1.31.9', 'v1.31.10']).

    Returns:
        str: The highest version string.
    """
    return max(versions, key=lambda v: tuple(int(x) for x in v.lstrip("v").split(".")))


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


def _run_step(
    ssh_connection: SSHConnection,
    kube_upgrade_keywords: KubeUpgradeKeywords,
    kube_upgrade_show_keywords: KubeUpgradeShowKeywords,
    step_name: str,
    active_controller: str,
    wait_for_completion: bool = True,
    timeout: int = 600,
) -> None:
    """Execute a kube upgrade step, optionally waiting for its completed state.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        kube_upgrade_keywords (KubeUpgradeKeywords): KubeUpgradeKeywords instance.
        kube_upgrade_show_keywords (KubeUpgradeShowKeywords): KubeUpgradeShowKeywords instance.
        step_name (str): One of the STEP_* constants.
        active_controller (str): Hostname of the active controller.
        wait_for_completion (bool): If True, wait for the step to reach its completed state.
        timeout (int): Max wait time for step completion.
    """
    get_logger().log_test_case_step(f"Run step: {step_name}")
    if step_name == STEP_DOWNLOAD_IMAGES:
        kube_upgrade_keywords.kube_upgrade_download_images()
    elif step_name == STEP_PRE_APPLICATION_UPDATE:
        kube_upgrade_keywords.kube_pre_application_update()
    elif step_name == STEP_UPGRADE_NETWORKING:
        kube_upgrade_keywords.kube_upgrade_networking()
    elif step_name == STEP_UPGRADE_STORAGE:
        kube_upgrade_keywords.kube_upgrade_storage()
    elif step_name == STEP_CONTROL_PLANE:
        kube_host_upgrade_keywords = KubeHostUpgradeKeywords(ssh_connection)
        kube_host_upgrade_keywords.kube_host_upgrade_control_plane(active_controller)

    if wait_for_completion:
        completed_state, failure_states = _STEP_TABLE[step_name]
        get_logger().log_test_case_step(f"Wait for '{completed_state}' state")
        kube_upgrade_show_keywords.wait_for_kube_upgrade_state(completed_state, timeout=timeout, failure_states=failure_states)


def _abort_during_combined_upgrade_step(
    request: FixtureRequest,
    abort_after_step: Optional[str],
    wait_for_completion: bool = False,
    timeout: int = 600,
) -> None:
    """Abort a combined upgrade at a specific step and verify cleanup.

    This helper encapsulates the full test lifecycle:
    1. Setup: get available release/version, start combined upgrade.
    2. Run prerequisite steps up to (but not including) abort_after_step.
    3. Send the abort_after_step command (unless None — abort right after start).
    4. If wait_for_completion, wait for the step to finish before aborting.
    5. Abort, wait for upgrade-aborted, and clean up.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown registration.
        abort_after_step (Optional[str]): The step at which to abort (one of STEP_*
            constants), or None to abort immediately after kube-upgrade-start.
        wait_for_completion (bool): If True, wait for the step to complete before aborting.
        timeout (int): Maximum wait time for state transitions.
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Get available software release")
    software_list_output = SoftwareListKeywords(ssh_connection).get_software_list()
    available_releases = software_list_output.get_release_name_by_state("available")
    validate_not_equals(available_releases, [], "At least one release in 'available' state must exist")
    target_platform_release = available_releases[0]

    get_logger().log_setup_step("Get highest available Kubernetes version")
    kube_version_output = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list()
    available_versions = kube_version_output.get_version_by_state("available")
    target_kube_version = _highest_kube_version(available_versions)
    get_logger().log_info(f"Target: platform={target_platform_release}, kube={target_kube_version}")

    usm_keywords = USMKeywords(ssh_connection)
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()
    get_logger().log_info(f"Active controller: {active_controller}")

    # --- Register independent teardown finalizers (LIFO order) ---
    def teardown_system_deploy() -> None:
        get_logger().log_teardown_step("Delete system deploy if needed")
        try:
            usm_keywords.system_deploy_delete()
        except Exception:
            get_logger().log_info("No system deploy to delete")

    def teardown_kube_upgrade() -> None:
        get_logger().log_teardown_step("Abort kubernetes upgrade if needed")
        try:
            kube_upgrade_keywords.kube_upgrade_abort()
        except Exception:
            get_logger().log_info("No kubernetes upgrade to abort")
            return
        try:
            kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-aborted", timeout=300)
        except Exception:
            get_logger().log_info("Timed out waiting for upgrade-aborted state")
        get_logger().log_teardown_step("Delete kubernetes upgrade if needed")
        try:
            kube_upgrade_keywords.kube_upgrade_delete()
        except Exception:
            get_logger().log_info("No kubernetes upgrade to delete")

    request.addfinalizer(teardown_system_deploy)
    request.addfinalizer(teardown_kube_upgrade)

    # --- Start combined upgrade ---
    get_logger().log_test_case_step(f"Initialize combined upgrade: system-deploy init {target_platform_release} --kube-upgrade {target_kube_version}")
    usm_keywords.system_deploy_init(target_platform_release, kube_upgrade=target_kube_version)

    get_logger().log_test_case_step(f"Start Kubernetes upgrade to {target_kube_version}")
    kube_upgrade_keywords.kube_upgrade_start(target_kube_version)

    # --- Run prerequisite steps and the abort step ---
    if abort_after_step is not None:
        step_index = _STEP_ORDER.index(abort_after_step)

        # Run all prerequisite steps to completion
        for prerequisite_step in _STEP_ORDER[:step_index]:
            _run_step(ssh_connection, kube_upgrade_keywords, kube_upgrade_show_keywords, prerequisite_step, active_controller, timeout=timeout)

        # Run the abort step itself
        _run_step(ssh_connection, kube_upgrade_keywords, kube_upgrade_show_keywords, abort_after_step, active_controller, wait_for_completion=wait_for_completion, timeout=timeout)

    # --- Abort and cleanup ---
    get_logger().log_test_case_step("Abort the Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_abort()

    get_logger().log_test_case_step("Wait for upgrade-aborted state")
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-aborted", timeout=timeout)

    get_logger().log_test_case_step("Delete the Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_delete()

    get_logger().log_test_case_step("Delete the system deploy")
    usm_keywords.system_deploy_delete()

    AlarmListKeywords(ssh_connection).wait_for_all_alarms_cleared()


# =============================================================================
# Tests: Abort immediately after kube-upgrade-start
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_kube_upgrade_start(request: FixtureRequest) -> None:
    """Test aborting a combined upgrade immediately after kube-upgrade-start.

    Preconditions:
        - Lab is simplex with a combined upgrade available

    Setup:
        - Establish SSH connection to active controller
        - Get available software release and Kubernetes version

    Test Steps:
        1. Initialize combined upgrade via system-deploy init
        2. Start Kubernetes upgrade
        3. Abort the Kubernetes upgrade
        4. Wait for upgrade-aborted state
        5. Delete Kubernetes upgrade and system deploy

    Teardown:
        - Abort and delete kubernetes upgrade if needed
        - Delete system deploy if needed
    """
    _abort_during_combined_upgrade_step(request, abort_after_step=None)


# =============================================================================
# Tests: Abort after kube-upgrade-download-images
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_immediately_after_download_images(request: FixtureRequest) -> None:
    """Test aborting immediately after sending kube-upgrade-download-images.

    Preconditions:
        - Lab is simplex with a combined upgrade available

    Setup:
        - Establish SSH connection to active controller
        - Get available software release and Kubernetes version

    Test Steps:
        1. Initialize combined upgrade via system-deploy init
        2. Start Kubernetes upgrade
        3. Send kube-upgrade-download-images command
        4. Immediately abort the Kubernetes upgrade
        5. Wait for upgrade-aborted state
        6. Delete Kubernetes upgrade and system deploy

    Teardown:
        - Abort and delete kubernetes upgrade if needed
        - Delete system deploy if needed
    """
    _abort_during_combined_upgrade_step(request, abort_after_step=STEP_DOWNLOAD_IMAGES, wait_for_completion=False)


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_download_images_completed(request: FixtureRequest) -> None:
    """Test aborting after kube-upgrade-download-images has completed.

    Preconditions:
        - Lab is simplex with a combined upgrade available

    Setup:
        - Establish SSH connection to active controller
        - Get available software release and Kubernetes version

    Test Steps:
        1. Initialize combined upgrade via system-deploy init
        2. Start Kubernetes upgrade
        3. Send kube-upgrade-download-images and wait for completion
        4. Abort the Kubernetes upgrade
        5. Wait for upgrade-aborted state
        6. Delete Kubernetes upgrade and system deploy

    Teardown:
        - Abort and delete kubernetes upgrade if needed
        - Delete system deploy if needed
    """
    _abort_during_combined_upgrade_step(request, abort_after_step=STEP_DOWNLOAD_IMAGES, wait_for_completion=True)


# =============================================================================
# Tests: Abort after kube-pre-application-update
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_immediately_after_pre_application_update(request: FixtureRequest) -> None:
    """Test aborting immediately after sending kube-pre-application-update.

    Preconditions:
        - Lab is simplex with a combined upgrade available

    Setup:
        - Establish SSH connection to active controller
        - Get available software release and Kubernetes version

    Test Steps:
        1. Initialize combined upgrade via system-deploy init
        2. Start Kubernetes upgrade
        3. Download images and wait for completion
        4. Send kube-pre-application-update command
        5. Immediately abort the Kubernetes upgrade
        6. Wait for upgrade-aborted state
        7. Delete Kubernetes upgrade and system deploy

    Teardown:
        - Abort and delete kubernetes upgrade if needed
        - Delete system deploy if needed
    """
    _abort_during_combined_upgrade_step(request, abort_after_step=STEP_PRE_APPLICATION_UPDATE, wait_for_completion=False)


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_pre_application_update_completed(request: FixtureRequest) -> None:
    """Test aborting after kube-pre-application-update has completed.

    Preconditions:
        - Lab is simplex with a combined upgrade available

    Setup:
        - Establish SSH connection to active controller
        - Get available software release and Kubernetes version

    Test Steps:
        1. Initialize combined upgrade via system-deploy init
        2. Start Kubernetes upgrade
        3. Download images and wait for completion
        4. Send kube-pre-application-update and wait for completion
        5. Abort the Kubernetes upgrade
        6. Wait for upgrade-aborted state
        7. Delete Kubernetes upgrade and system deploy

    Teardown:
        - Abort and delete kubernetes upgrade if needed
        - Delete system deploy if needed
    """
    _abort_during_combined_upgrade_step(request, abort_after_step=STEP_PRE_APPLICATION_UPDATE, wait_for_completion=True)


# =============================================================================
# Tests: Abort after kube-upgrade-networking
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_immediately_after_upgrade_networking(request: FixtureRequest) -> None:
    """Test aborting immediately after sending kube-upgrade-networking.

    Preconditions:
        - Lab is simplex with a combined upgrade available

    Setup:
        - Establish SSH connection to active controller
        - Get available software release and Kubernetes version

    Test Steps:
        1. Initialize combined upgrade via system-deploy init
        2. Start Kubernetes upgrade
        3. Download images and wait for completion
        4. Pre-application-update and wait for completion
        5. Send kube-upgrade-networking command
        6. Immediately abort the Kubernetes upgrade
        7. Wait for upgrade-aborted state
        8. Delete Kubernetes upgrade and system deploy

    Teardown:
        - Abort and delete kubernetes upgrade if needed
        - Delete system deploy if needed
    """
    _abort_during_combined_upgrade_step(request, abort_after_step=STEP_UPGRADE_NETWORKING, wait_for_completion=False)


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_upgrade_networking_completed(request: FixtureRequest) -> None:
    """Test aborting after kube-upgrade-networking has completed.

    Preconditions:
        - Lab is simplex with a combined upgrade available

    Setup:
        - Establish SSH connection to active controller
        - Get available software release and Kubernetes version

    Test Steps:
        1. Initialize combined upgrade via system-deploy init
        2. Start Kubernetes upgrade
        3. Download images and wait for completion
        4. Pre-application-update and wait for completion
        5. Send kube-upgrade-networking and wait for completion
        6. Abort the Kubernetes upgrade
        7. Wait for upgrade-aborted state
        8. Delete Kubernetes upgrade and system deploy

    Teardown:
        - Abort and delete kubernetes upgrade if needed
        - Delete system deploy if needed
    """
    _abort_during_combined_upgrade_step(request, abort_after_step=STEP_UPGRADE_NETWORKING, wait_for_completion=True)


# =============================================================================
# Tests: Abort after kube-upgrade-storage
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_immediately_after_upgrade_storage(request: FixtureRequest) -> None:
    """Test aborting immediately after sending kube-upgrade-storage.

    Preconditions:
        - Lab is simplex with a combined upgrade available

    Setup:
        - Establish SSH connection to active controller
        - Get available software release and Kubernetes version

    Test Steps:
        1. Initialize combined upgrade via system-deploy init
        2. Start Kubernetes upgrade
        3. Download images and wait for completion
        4. Pre-application-update and wait for completion
        5. Networking upgrade and wait for completion
        6. Send kube-upgrade-storage command
        7. Immediately abort the Kubernetes upgrade
        8. Wait for upgrade-aborted state
        9. Delete Kubernetes upgrade and system deploy

    Teardown:
        - Abort and delete kubernetes upgrade if needed
        - Delete system deploy if needed
    """
    _abort_during_combined_upgrade_step(request, abort_after_step=STEP_UPGRADE_STORAGE, wait_for_completion=False)


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_upgrade_storage_completed(request: FixtureRequest) -> None:
    """Test aborting after kube-upgrade-storage has completed.

    Preconditions:
        - Lab is simplex with a combined upgrade available

    Setup:
        - Establish SSH connection to active controller
        - Get available software release and Kubernetes version

    Test Steps:
        1. Initialize combined upgrade via system-deploy init
        2. Start Kubernetes upgrade
        3. Download images and wait for completion
        4. Pre-application-update and wait for completion
        5. Networking upgrade and wait for completion
        6. Send kube-upgrade-storage and wait for completion
        7. Abort the Kubernetes upgrade
        8. Wait for upgrade-aborted state
        9. Delete Kubernetes upgrade and system deploy

    Teardown:
        - Abort and delete kubernetes upgrade if needed
        - Delete system deploy if needed
    """
    _abort_during_combined_upgrade_step(request, abort_after_step=STEP_UPGRADE_STORAGE, wait_for_completion=True)


# =============================================================================
# Tests: Abort after kube-host-upgrade control-plane
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_immediately_after_host_upgrade_control_plane(request: FixtureRequest) -> None:
    """Test aborting immediately after sending kube-host-upgrade control-plane.

    Preconditions:
        - Lab is simplex with a combined upgrade available

    Setup:
        - Establish SSH connection to active controller
        - Get available software release and Kubernetes version

    Test Steps:
        1. Initialize combined upgrade via system-deploy init
        2. Start Kubernetes upgrade
        3. Download images and wait for completion
        4. Pre-application-update and wait for completion
        5. Networking upgrade and wait for completion
        6. Storage upgrade and wait for completion
        7. Send kube-host-upgrade control-plane command
        8. Immediately abort the Kubernetes upgrade
        9. Wait for upgrade-aborted state
        10. Delete Kubernetes upgrade and system deploy

    Teardown:
        - Abort and delete kubernetes upgrade if needed
        - Delete system deploy if needed
    """
    _abort_during_combined_upgrade_step(request, abort_after_step=STEP_CONTROL_PLANE, wait_for_completion=False)


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_abort_after_host_upgrade_control_plane_completed(request: FixtureRequest) -> None:
    """Test aborting after kube-host-upgrade control-plane completed with rollback verification.

    Preconditions:
        - Lab is simplex with a combined upgrade available

    Setup:
        - Establish SSH connection to active controller
        - Get available software release and Kubernetes version
        - Record control-plane and etcd versions before upgrade

    Test Steps:
        1. Initialize combined upgrade via system-deploy init
        2. Start Kubernetes upgrade
        3. Download images and wait for completion
        4. Pre-application-update and wait for completion
        5. Networking upgrade and wait for completion
        6. Storage upgrade and wait for completion
        7. Send kube-host-upgrade control-plane and wait for completion
        8. Abort the Kubernetes upgrade
        9. Wait for upgrade-aborted state
        10. Verify control-plane version rolled back to original
        11. Verify etcd version rolled back to original
        12. Delete Kubernetes upgrade and system deploy

    Teardown:
        - Abort and delete kubernetes upgrade if needed
        - Delete system deploy if needed
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_setup_step("Record control-plane version before upgrade")
    original_control_plane_version = _get_control_plane_version(ssh_connection, active_controller)
    get_logger().log_info(f"Control-plane version before upgrade: {original_control_plane_version}")

    get_logger().log_setup_step("Record etcd version before upgrade")
    original_etcd_version = _get_etcd_version(ssh_connection)
    get_logger().log_info(f"Etcd version before upgrade: {original_etcd_version}")

    _abort_during_combined_upgrade_step(request, abort_after_step=STEP_CONTROL_PLANE, wait_for_completion=True)

    get_logger().log_test_case_step("Verify control-plane version rolled back to original")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    rollback_version = _get_control_plane_version(ssh_connection, active_controller)
    get_logger().log_info(f"Control-plane version after abort: {rollback_version}")
    validate_equals(rollback_version, original_control_plane_version, "Control-plane version rolled back to original")

    get_logger().log_test_case_step("Verify etcd version rolled back to original")
    rollback_etcd_version = _get_etcd_version(ssh_connection)
    get_logger().log_info(f"Etcd version after abort: {rollback_etcd_version}")
    validate_equals(rollback_etcd_version, original_etcd_version, "Etcd version rolled back to original")
