"""
Validate manual Kubernetes-upgrade abort scenarios.

A manual Kubernetes upgrade is a linear sequence of CLI commands, each advancing the
``system kube-upgrade-show`` state (or, for kubelet, the per-host status in
``system kube-host-upgrade-list``). These tests drive that sequence forward to a chosen
step and then exercise an abort:

1. Rollback scenarios (abort permitted, up to and including ``uncordon-complete``). The
   test runs the sequence to the step, aborts, deletes the upgrade, and verifies BOTH the
   etcd version and the Kubernetes (control-plane) version returned to their originals.

2. Abort-rejection scenarios (steps after host uncordon: ``upgrade-complete`` and
   ``post-updated-apps``). The platform refuses to abort once the upgrade reaches the
   completion phase. These tests drive the full upgrade through the completion step, attempt
   the abort, and verify it is rejected with the state-specific message, the upgrade is NOT
   rolled back, and the active Kubernetes version is the upgrade target.

A single ``kube-host-upgrade control-plane`` advances the control-plane by one minor
version and the control-plane may lead the kubelet by at most three minor versions, so the
control-plane and kubelet phases are driven in batches via ``build_control_plane_batches``
(mirroring ``testcases/cloud_platform/upgrade/k8s_upgrade/test_kube_upgrade_manual.py``).

Prerequisites:
    - Runs on a simplex lab with a Kubernetes version available to upgrade to.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.exceptions.validation_failure_error import ValidationFailureError
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_list_contains, validate_not_equals, validate_not_none, validate_str_contains
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.health_query.system_health_query_keywords import SystemHealthQueryKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_keywords import KubeHostUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_list_keywords import KubeHostUpgradeListKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_keywords import KubeUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_show_keywords import KubeUpgradeShowKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_utils import build_control_plane_batches
from keywords.cloud_platform.system.kubernetes.kube_upgrade_verification import get_control_plane_version, get_etcd_version, verify_kube_and_etcd_versions_rolled_back
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords

# =============================================================================
# Constants
# =============================================================================

# Kube-upgrade states (kube-upgrade-show 'state' column).
STATE_UPGRADE_STARTED = "upgrade-started"
STATE_DOWNLOADED_IMAGES = "downloaded-images"
STATE_PRE_UPDATED_APPS = "pre-updated-apps"
STATE_UPGRADED_NETWORKING = "upgraded-networking"
STATE_UPGRADED_STORAGE = "upgraded-storage"
STATE_CORDON_COMPLETE = "cordon-complete"
STATE_UPGRADED_FIRST_MASTER = "upgraded-first-master"
STATE_UNCORDON_COMPLETE = "uncordon-complete"
STATE_UPGRADE_COMPLETE = "upgrade-complete"
STATE_POST_UPDATED_APPS = "post-updated-apps"
STATE_UPGRADE_ABORTED = "upgrade-aborted"

# Per-host kubelet status (kube-host-upgrade-list 'status' column).
HOST_STATUS_UPGRADED_KUBELET = "upgraded-kubelet"

# Failure states that fast-fail a wait for a step's completed state.
FAILURE_DOWNLOADING_IMAGES = ["downloading-images-failed"]
FAILURE_PRE_UPDATING_APPS = ["pre-updating-apps-failed"]
FAILURE_UPGRADING_NETWORKING = ["upgrading-networking-failed"]
FAILURE_UPGRADING_STORAGE = ["upgrading-storage-failed"]
FAILURE_CORDON = ["cordon-failed"]
FAILURE_UPGRADING_FIRST_MASTER = ["upgrading-first-master-failed"]
FAILURE_UPGRADING_KUBELET = ["upgrading-kubelets-failed"]
FAILURE_UNCORDON = ["uncordon-failed"]
FAILURE_POST_UPDATING_APPS = ["post-updating-apps-failed"]

# Alarm raised while a kube upgrade is in progress; ignored when waiting for cleanup.
KUBE_UPGRADE_IN_PROGRESS_ALARM = "900.007"

# Default per-state transition timeout.
DEFAULT_TIMEOUT = 600

# Exceptions a best-effort teardown step tolerates so each cleanup action runs
# independently. Keyword calls raise KeywordException; the wait/validation helpers raise
# TimeoutError, ValidationFailureError, or AssertionError when a state is not reached.
TEARDOWN_TOLERATED_EXCEPTIONS = (KeywordException, ValidationFailureError, TimeoutError, AssertionError)

# =============================================================================
# Stop-point constants (sequence order)
# =============================================================================

# The step a test drives to before aborting. Steps up to and including uncordon permit
# the abort (rollback); steps after uncordon reject it (completion phase). Control-plane
# and kubelet are separate stop points so a test can abort during/at either phase; an "at
# kubelet" abort means the control-plane and kubelet have reached the target version.
STEP_DOWNLOAD_IMAGES = 1
STEP_PRE_APPLICATION_UPDATE = 2
STEP_UPGRADE_NETWORKING = 3
STEP_UPGRADE_STORAGE = 4
STEP_HOST_CORDON = 5
STEP_CONTROL_PLANE = 6
STEP_KUBELET = 7
STEP_HOST_UNCORDON = 8
STEP_KUBE_UPGRADE_COMPLETE = 9
STEP_KUBE_POST_APPLICATION_UPDATE = 10

# Last step whose abort is permitted (rollback). Beyond this the abort is rejected.
LAST_ROLLBACK_STEP = STEP_HOST_UNCORDON

# Completion-phase steps map to the kube-upgrade-show state the abort is rejected at.
REJECTED_STATE_BY_STEP = {
    STEP_KUBE_UPGRADE_COMPLETE: STATE_UPGRADE_COMPLETE,
    STEP_KUBE_POST_APPLICATION_UPDATE: STATE_POST_UPDATED_APPS,
}


# =============================================================================
# Helpers: control-plane upgrade
# =============================================================================


def _upgrade_control_plane_once(
    kube_host_upgrade_keywords: KubeHostUpgradeKeywords,
    kube_upgrade_show_keywords: KubeUpgradeShowKeywords,
    host: str,
    wait: bool,
    timeout: int,
    log: str = "Upgrade control-plane",
) -> None:
    """Send one control-plane upgrade (one minor version) and optionally wait for completion.

    Args:
        kube_host_upgrade_keywords (KubeHostUpgradeKeywords): kube-host-upgrade keywords.
        kube_upgrade_show_keywords (KubeUpgradeShowKeywords): kube-upgrade-show keywords.
        host (str): Active controller hostname.
        wait (bool): If True, wait for the ``upgraded-first-master`` completed state.
        timeout (int): Maximum wait time in seconds for the state transition.
        log (str): Test-step log message for the upgrade command.
    """
    get_logger().log_test_case_step(log)
    kube_host_upgrade_keywords.kube_host_upgrade_control_plane(host)
    if wait:
        kube_upgrade_show_keywords.wait_for_kube_upgrade_state(STATE_UPGRADED_FIRST_MASTER, timeout=timeout, failure_states=FAILURE_UPGRADING_FIRST_MASTER)


# =============================================================================
# Driver: run the upgrade sequence to a step
# =============================================================================


def _run_sequence_to_step(
    ssh_connection: SSHConnection,
    host: str,
    stop_step: int,
    wait_for_completion: bool,
    active_kube_version: str,
    target_version: str,
    available_kube_versions: list,
    timeout: int,
) -> None:
    """Run the manual upgrade commands in order up to and including ``stop_step``.

    kube-upgrade-start has already run. Each step before the stop is waited to its completed
    state. The stop step's handling depends on ``wait_for_completion``:

    - ``wait_for_completion=True`` ("at"): the stop command is sent and waited to its
      completed state, so the caller aborts at a stable checkpoint.
    - ``wait_for_completion=False`` ("during"): the stop command is sent and the function
      returns IMMEDIATELY with no intervening command, so the caller aborts while the step is
      still in flight. No confirmation wait is done — any extra SSH round-trip adds latency
      that could let a fast step complete server-side before the abort is processed.

    The control-plane and kubelet phases are driven to the target in batches so a target two
    or more minor versions ahead is handled correctly. A "during control-plane" stop sends
    only the first control-plane upgrade and returns; a "during kubelet" stop drives the
    control-plane to target, sends the final kubelet upgrade, and returns.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        host (str): Active controller hostname (the single host upgraded on simplex).
        stop_step (int): Step to stop after (a STEP_* constant). Completion-phase stops run
            the whole sequence through uncordon.
        wait_for_completion (bool): If True, wait for the stop step's completed state ("at");
            if False, return immediately after sending the stop command ("during").
        active_kube_version (str): Active Kubernetes version before the upgrade.
        target_version (str): Target Kubernetes version for the upgrade.
        available_kube_versions (list): Versions reported as 'available' by kube-version-list.
        timeout (int): Maximum wait time in seconds for each state transition.
    """
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_host_upgrade_keywords = KubeHostUpgradeKeywords(ssh_connection)
    kube_host_upgrade_list_keywords = KubeHostUpgradeListKeywords(ssh_connection)

    # Completion-phase stops run the whole sequence through uncordon to completion.
    effective_stop = min(stop_step, STEP_HOST_UNCORDON)

    # Ordered steps that advance a kube-upgrade-show state (download through cordon). Each
    # entry is (STEP_* constant, step log, command callable, completed_state, failure_states).
    steps = [
        (STEP_DOWNLOAD_IMAGES, "Download Kubernetes images", lambda: kube_upgrade_keywords.kube_upgrade_download_images(), STATE_DOWNLOADED_IMAGES, FAILURE_DOWNLOADING_IMAGES),
        (STEP_PRE_APPLICATION_UPDATE, "Run pre-application-update", lambda: kube_upgrade_keywords.kube_pre_application_update(), STATE_PRE_UPDATED_APPS, FAILURE_PRE_UPDATING_APPS),
        (STEP_UPGRADE_NETWORKING, "Upgrade networking", lambda: kube_upgrade_keywords.kube_upgrade_networking(), STATE_UPGRADED_NETWORKING, FAILURE_UPGRADING_NETWORKING),
        (STEP_UPGRADE_STORAGE, "Upgrade storage", lambda: kube_upgrade_keywords.kube_upgrade_storage(), STATE_UPGRADED_STORAGE, FAILURE_UPGRADING_STORAGE),
        (STEP_HOST_CORDON, "Host cordon", lambda: kube_upgrade_keywords.kube_host_cordon(host), STATE_CORDON_COMPLETE, FAILURE_CORDON),
    ]

    for step, step_log, command, completed_state, failure_states in steps:
        get_logger().log_test_case_step(step_log)
        command()
        # "during" cut-off: return immediately with no intervening command so the caller
        # aborts in-flight. Any extra SSH round-trip could let a fast step complete first.
        if step == effective_stop and not wait_for_completion:
            return
        get_logger().log_test_case_step(f"Wait for completed state '{completed_state}'")
        kube_upgrade_show_keywords.wait_for_kube_upgrade_state(completed_state, timeout=timeout, failure_states=failure_states)
        if step == effective_stop:
            return

    # Control-plane + kubelet, driven to the target version in batches of at most three
    # minor versions (the control-plane may lead the kubelet by at most three minors).
    all_versions = available_kube_versions + [active_kube_version]
    batches = build_control_plane_batches(active_kube_version, target_version, all_versions)
    get_logger().log_info(f"Control-plane upgrade batches: {batches}")

    # Control-plane cut-off: exercise only the first control-plane upgrade (a single minor
    # step). "during" aborts in-flight (no wait); "at" aborts after upgraded-first-master.
    if effective_stop == STEP_CONTROL_PLANE:
        _upgrade_control_plane_once(kube_host_upgrade_keywords, kube_upgrade_show_keywords, host, wait_for_completion, timeout)
        return

    # Kubelet and beyond require the control-plane at target, so drive the full batches.
    for batch_num, batch in enumerate(batches, 1):
        for version in batch:
            get_logger().log_info(f"Upgrading control-plane to {version}")
            _upgrade_control_plane_once(kube_host_upgrade_keywords, kube_upgrade_show_keywords, host, True, timeout, log=f"Upgrade control-plane (batch {batch_num}/{len(batches)})")
        get_logger().log_test_case_step(f"Upgrade kubelet (batch {batch_num}/{len(batches)})")
        kube_host_upgrade_keywords.kube_host_upgrade_kubelet(host)
        # "during kubelet": on the final batch, send the kubelet upgrade and abort in-flight
        # (skip the status wait). Earlier batches must complete so the next batch can proceed.
        if effective_stop == STEP_KUBELET and not wait_for_completion and batch_num == len(batches):
            return
        kube_host_upgrade_list_keywords.wait_for_host_upgrade_status(host, HOST_STATUS_UPGRADED_KUBELET, timeout=timeout, failure_statuses=FAILURE_UPGRADING_KUBELET)
    if effective_stop == STEP_KUBELET:
        return

    # Host uncordon.
    get_logger().log_test_case_step("Host uncordon")
    kube_upgrade_keywords.kube_host_uncordon(host)
    get_logger().log_test_case_step(f"Wait for completed state '{STATE_UNCORDON_COMPLETE}'")
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(STATE_UNCORDON_COMPLETE, timeout=timeout, failure_states=FAILURE_UNCORDON)


# =============================================================================
# Helper: cleanup kubernetes upgrade in teardown
# =============================================================================


def _cleanup_kubernetes_upgrade(
    expect_rejected: bool,
    kube_upgrade_show_keywords: KubeUpgradeShowKeywords,
    kube_upgrade_keywords: KubeUpgradeKeywords,
    timeout: int,
) -> None:
    """Clean up the Kubernetes upgrade based on the scenario type.

    This function handles two distinct cleanup paths:
    - Rejection scenarios: Complete any remaining steps and delete the upgrade
    - Rollback scenarios: Abort and delete the upgrade

    Args:
        expect_rejected (bool): True for completion-phase tests (abort rejected),
            False for rollback tests (abort permitted).
        kube_upgrade_show_keywords (KubeUpgradeShowKeywords): Keywords for checking upgrade state.
        kube_upgrade_keywords (KubeUpgradeKeywords): Keywords for upgrade operations.
        timeout (int): Maximum wait time in seconds for state transitions.
    """
    get_logger().log_teardown_step("Clean up kubernetes upgrade if needed")

    # For rejection scenarios (completion-phase tests): the abort is not permitted,
    # so we finish any remaining completion step and delete the upgrade
    if expect_rejected:
        if not kube_upgrade_show_keywords.is_kube_upgrade_in_progress():
            get_logger().log_info("No kubernetes upgrade present")
            return
        current_state = kube_upgrade_show_keywords.kube_upgrade_show().get_kube_upgrade_show_object().get_state()
        # If stopped at upgrade-complete, run the post-application-update step
        if current_state == STATE_UPGRADE_COMPLETE:
            try:
                kube_upgrade_keywords.kube_post_application_update()
                kube_upgrade_show_keywords.wait_for_kube_upgrade_state(STATE_POST_UPDATED_APPS, timeout=timeout, failure_states=FAILURE_POST_UPDATING_APPS)
            except TEARDOWN_TOLERATED_EXCEPTIONS:
                get_logger().log_info("post-application-update not applicable during teardown")
    # For rollback scenarios: abort (if needed) and delete the upgrade
    else:
        try:
            kube_upgrade_keywords.kube_upgrade_abort()
            kube_upgrade_show_keywords.wait_for_kube_upgrade_state(STATE_UPGRADE_ABORTED, timeout=300)
        except TEARDOWN_TOLERATED_EXCEPTIONS:
            get_logger().log_info("No kubernetes upgrade to abort")

    # Delete the upgrade regardless of the scenario type
    try:
        kube_upgrade_keywords.kube_upgrade_delete()
    except TEARDOWN_TOLERATED_EXCEPTIONS:
        get_logger().log_info("No kubernetes upgrade to delete")


# =============================================================================
# Driver: run to a step, abort, and verify the rollback or rejection
# =============================================================================


def _run_abort_scenario(request: FixtureRequest, stop_step: int, wait_for_completion: bool = True, timeout: int = DEFAULT_TIMEOUT) -> None:
    """Drive the manual Kubernetes upgrade to ``stop_step``, abort, and verify the outcome.

    Rollback (``stop_step <= LAST_ROLLBACK_STEP``): aborts, deletes, and verifies BOTH the
    etcd version and the Kubernetes (control-plane) version returned to their originals, and
    that alarms clear. ``wait_for_completion`` selects the cut-off: True ("at") aborts once
    the stop step has reached its completed state; False ("during") aborts immediately after
    sending the stop command, while it is still in flight.

    Abort-rejection (completion phase): drives the full upgrade through the completion step,
    attempts the abort, and verifies it is rejected with the state-specific message, the
    upgrade is NOT rolled back, and the active Kubernetes version is the target.
    ``wait_for_completion`` is not applicable and is ignored.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.
        stop_step (int): Step to drive to before aborting (a STEP_* constant).
        wait_for_completion (bool): If True, abort once the stop step completes ("at"); if
            False, abort immediately after sending the stop command ("during"). Ignored for
            completion-phase steps. Defaults to True.
        timeout (int): Maximum wait time in seconds for each state transition.
    """
    expect_rejected = stop_step > LAST_ROLLBACK_STEP

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    def teardown() -> None:
        """Clean up the kubernetes upgrade if it is still present.

        For rollback scenarios this aborts (if needed) and deletes. For rejection scenarios
        the abort is not permitted, so it finishes any remaining completion step and deletes,
        leaving the lab in a consistent (upgraded) state.
        """
        _cleanup_kubernetes_upgrade(expect_rejected, kube_upgrade_show_keywords, kube_upgrade_keywords, timeout)

    request.addfinalizer(teardown)

    get_logger().log_setup_step("Check if the system is healthy for Kubernetes upgrade")
    SystemHealthQueryKeywords(ssh_connection).is_system_healthy_for_kube_upgrade()

    get_logger().log_setup_step("Validate active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")

    target_version = kubernetes_upgrade_config.resolve_target_version(available_kube_versions)
    get_logger().log_info(f"Resolved target Kubernetes version: {target_version}")
    validate_list_contains(target_version, available_kube_versions, "Target version is in available list")

    get_logger().log_setup_step("Record original etcd and Kubernetes versions")
    original_etcd_version = get_etcd_version(ssh_connection)
    original_kube_version = get_control_plane_version(ssh_connection, host)
    get_logger().log_info(f"Original etcd version: {original_etcd_version}")
    get_logger().log_info(f"Original Kubernetes (control-plane) version: {original_kube_version}")

    get_logger().log_test_case_step(f"Start Kubernetes upgrade to {target_version}")
    start_output = kube_upgrade_keywords.kube_upgrade_start(target_version)
    validate_equals(start_output.get_kube_upgrade_show_object().get_state(), STATE_UPGRADE_STARTED, "Upgrade started")

    # Run the upgrade sequence up to the specified stop step
    _run_sequence_to_step(ssh_connection, host, stop_step, wait_for_completion, active_kube_version, target_version, available_kube_versions, timeout)

    # For completion-phase tests, verify abort is rejected and return early
    if expect_rejected:
        _complete_and_verify_abort_rejected(ssh_connection, stop_step, target_version, timeout)
        return

    get_logger().log_test_case_step("Abort the Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_abort()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(STATE_UPGRADE_ABORTED, timeout=timeout)

    get_logger().log_test_case_step("Delete the aborted Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_delete()

    # Use a fresh SSH connection inside the helper — the abort/rollback may have reset it.
    verify_kube_and_etcd_versions_rolled_back(host, original_kube_version, original_etcd_version)

    get_logger().log_test_case_step("Verify active Kubernetes version is unchanged")
    current_active_version = system_kube_keywords.get_system_kube_version_list().get_active_kubernetes_version()
    validate_equals(current_active_version, active_kube_version, "Active Kubernetes version unchanged after abort")

    get_logger().log_test_case_step("Wait for all alarms to clear, excluding the kube-upgrade-in-progress alarm")
    AlarmListKeywords(ssh_connection).wait_for_all_alarms_cleared_excluding([KUBE_UPGRADE_IN_PROGRESS_ALARM])


def _complete_and_verify_abort_rejected(ssh_connection: SSHConnection, stop_step: int, target_version: str, timeout: int) -> None:
    """Drive the completion phase to ``stop_step`` and verify the abort is rejected.

    Runs ``kube-upgrade-complete`` (and, for the post-application-update step,
    ``kube-post-application-update``) to reach the completion-phase state, then attempts the
    abort and asserts it is rejected with the state-specific message, the upgrade is NOT
    rolled back, and the active Kubernetes version is the target.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        stop_step (int): Completion-phase step (a STEP_* constant > LAST_ROLLBACK_STEP).
        target_version (str): Target Kubernetes version for the upgrade.
        timeout (int): Maximum wait time in seconds for each state transition.
    """
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    rejected_state = REJECTED_STATE_BY_STEP[stop_step]

    get_logger().log_test_case_step("Complete the Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_complete()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(STATE_UPGRADE_COMPLETE, timeout=timeout)

    if rejected_state == STATE_POST_UPDATED_APPS:
        get_logger().log_test_case_step("Run post-application-update")
        kube_upgrade_keywords.kube_post_application_update()
        kube_upgrade_show_keywords.wait_for_kube_upgrade_state(STATE_POST_UPDATED_APPS, timeout=timeout, failure_states=FAILURE_POST_UPDATING_APPS)

    get_logger().log_test_case_step(f"Attempt to abort at '{rejected_state}' (expected to be rejected)")
    abort_output = kube_upgrade_keywords.kube_upgrade_abort_with_error()
    validate_str_contains("\n".join(abort_output), f"Cannot abort the kubernetes upgrade it is in {rejected_state} state", f"Abort rejected at '{rejected_state}'")

    get_logger().log_test_case_step("Verify the upgrade was not rolled back by the rejected abort")
    state_after_abort = kube_upgrade_show_keywords.kube_upgrade_show().get_kube_upgrade_show_object().get_state()
    # The abort is rejected, so the upgrade must not have rolled back. The platform may still
    # advance the completion phase on its own (e.g. upgrade-complete -> post-updated-apps), so
    # accept any completion-phase state; the key assertion is that it is not aborted.
    validate_not_equals(state_after_abort, STATE_UPGRADE_ABORTED, "Upgrade was not aborted/rolled back")
    validate_list_contains(state_after_abort, [STATE_UPGRADE_COMPLETE, STATE_POST_UPDATED_APPS], "Upgrade remains in the completion phase")

    get_logger().log_test_case_step(f"Verify active Kubernetes version advanced to target {target_version}")
    current_active_version = system_kube_keywords.get_system_kube_version_list().get_active_kubernetes_version()
    validate_equals(current_active_version, target_version, "Active Kubernetes version is the upgrade target (abort rejected)")


# =============================================================================
# Tests: abort permitted — verify etcd and Kubernetes versions roll back
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_manual_abort_during_downloading_images(request: FixtureRequest) -> None:
    """Abort while images are downloading and verify etcd and Kubernetes versions roll back.

    Test Steps:
        - Record original etcd and Kubernetes versions.
        - Start the upgrade and send download-images.
        - Abort immediately (in-flight), wait for upgrade-aborted, and delete the upgrade.
        - Verify the etcd and Kubernetes versions returned to their originals.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_abort_scenario(request, STEP_DOWNLOAD_IMAGES, wait_for_completion=False)


@mark.p2
@mark.lab_is_simplex
def test_manual_abort_at_download_images(request: FixtureRequest) -> None:
    """Abort after download-images and verify etcd and Kubernetes versions roll back.

    Test Steps:
        - Record original etcd and Kubernetes versions.
        - Start the upgrade and download images.
        - Abort, wait for upgrade-aborted, and delete the upgrade.
        - Verify the etcd and Kubernetes versions returned to their originals.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_abort_scenario(request, STEP_DOWNLOAD_IMAGES)


@mark.p2
@mark.lab_is_simplex
def test_manual_abort_at_pre_application_update(request: FixtureRequest) -> None:
    """Abort after pre-application-update and verify etcd and Kubernetes versions roll back.

    Test Steps:
        - Record original etcd and Kubernetes versions.
        - Start the upgrade, download images, run pre-application-update.
        - Abort, wait for upgrade-aborted, and delete the upgrade.
        - Verify the etcd and Kubernetes versions returned to their originals.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_abort_scenario(request, STEP_PRE_APPLICATION_UPDATE)


@mark.p2
@mark.lab_is_simplex
def test_manual_abort_during_upgrading_networking(request: FixtureRequest) -> None:
    """Abort while networking is upgrading and verify etcd and Kubernetes versions roll back.

    Test Steps:
        - Record original etcd and Kubernetes versions.
        - Start the upgrade through pre-application-update, then send upgrade-networking.
        - Abort immediately (in-flight), wait for upgrade-aborted, and delete the upgrade.
        - Verify the etcd and Kubernetes versions returned to their originals.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_abort_scenario(request, STEP_UPGRADE_NETWORKING, wait_for_completion=False)


@mark.p2
@mark.lab_is_simplex
def test_manual_abort_at_upgrade_networking(request: FixtureRequest) -> None:
    """Abort after networking upgrade and verify etcd and Kubernetes versions roll back.

    Test Steps:
        - Record original etcd and Kubernetes versions.
        - Start the upgrade through pre-application-update, then upgrade networking.
        - Abort, wait for upgrade-aborted, and delete the upgrade.
        - Verify the etcd and Kubernetes versions returned to their originals.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_abort_scenario(request, STEP_UPGRADE_NETWORKING)


@mark.p2
@mark.lab_is_simplex
def test_manual_abort_at_upgrade_storage(request: FixtureRequest) -> None:
    """Abort after storage upgrade and verify etcd and Kubernetes versions roll back.

    Test Steps:
        - Record original etcd and Kubernetes versions.
        - Start the upgrade through networking, then upgrade storage.
        - Abort, wait for upgrade-aborted, and delete the upgrade.
        - Verify the etcd and Kubernetes versions returned to their originals.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_abort_scenario(request, STEP_UPGRADE_STORAGE)


@mark.p2
@mark.lab_is_simplex
def test_manual_abort_during_host_cordon_in_progress(request: FixtureRequest) -> None:
    """Abort while the host cordon is in progress; verify etcd and Kubernetes roll back.

    Test Steps:
        - Record original etcd and Kubernetes versions.
        - Start the upgrade through storage, then send the host cordon.
        - Abort immediately (in-flight), wait for upgrade-aborted, and delete the upgrade.
        - Verify the etcd and Kubernetes versions returned to their originals.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_abort_scenario(request, STEP_HOST_CORDON, wait_for_completion=False)


@mark.p2
@mark.lab_is_simplex
def test_manual_abort_at_host_cordon(request: FixtureRequest) -> None:
    """Abort after host cordon and verify etcd and Kubernetes versions roll back.

    Test Steps:
        - Record original etcd and Kubernetes versions.
        - Start the upgrade through storage, then cordon the host.
        - Abort, wait for upgrade-aborted, and delete the upgrade.
        - Verify the etcd and Kubernetes versions returned to their originals.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_abort_scenario(request, STEP_HOST_CORDON)


@mark.p2
@mark.lab_is_simplex
def test_manual_abort_during_host_upgrade_control_plane(request: FixtureRequest) -> None:
    """Abort while the control-plane is upgrading; verify etcd and Kubernetes roll back.

    Test Steps:
        - Record original etcd and Kubernetes versions.
        - Start the upgrade through cordon, then send the first control-plane upgrade.
        - Abort immediately (in-flight), wait for upgrade-aborted, and delete the upgrade.
        - Verify the etcd and Kubernetes versions returned to their originals.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_abort_scenario(request, STEP_CONTROL_PLANE, wait_for_completion=False)


@mark.p2
@mark.lab_is_simplex
def test_manual_abort_at_host_upgrade_control_plane(request: FixtureRequest) -> None:
    """Abort after the first control-plane upgrade; verify etcd and Kubernetes roll back.

    Test Steps:
        - Record original etcd and Kubernetes versions.
        - Start the upgrade through cordon, then upgrade the control-plane (first master).
        - Abort, wait for upgrade-aborted, and delete the upgrade.
        - Verify the etcd and Kubernetes versions returned to their originals.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_abort_scenario(request, STEP_CONTROL_PLANE, wait_for_completion=True)


@mark.p2
@mark.lab_is_simplex
def test_manual_abort_during_kube_host_upgrading_kubelet(request: FixtureRequest) -> None:
    """Abort while the kubelet is upgrading; verify etcd and Kubernetes roll back.

    Test Steps:
        - Record original etcd and Kubernetes versions.
        - Start the upgrade through cordon, drive the control-plane to target, then send the
          final kubelet upgrade.
        - Abort immediately (in-flight), wait for upgrade-aborted, and delete the upgrade.
        - Verify the etcd and Kubernetes versions returned to their originals.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_abort_scenario(request, STEP_KUBELET, wait_for_completion=False)


@mark.p2
@mark.lab_is_simplex
def test_manual_abort_at_kube_host_upgrade_kubelet(request: FixtureRequest) -> None:
    """Abort after the control-plane and kubelet reach target; verify versions roll back.

    Test Steps:
        - Record original etcd and Kubernetes versions.
        - Start the upgrade through cordon, then upgrade control-plane and kubelet to target.
        - Abort, wait for upgrade-aborted, and delete the upgrade.
        - Verify the etcd and Kubernetes versions returned to their originals.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_abort_scenario(request, STEP_KUBELET, wait_for_completion=True)


@mark.p2
@mark.lab_is_simplex
def test_manual_abort_at_host_uncordon(request: FixtureRequest) -> None:
    """Abort after host uncordon and verify etcd and Kubernetes versions roll back.

    Test Steps:
        - Record original etcd and Kubernetes versions.
        - Start the upgrade through control-plane/kubelet, then uncordon the host.
        - Abort, wait for upgrade-aborted, and delete the upgrade.
        - Verify the etcd and Kubernetes versions returned to their originals.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _run_abort_scenario(request, STEP_HOST_UNCORDON)


# =============================================================================
# Tests: abort rejected — completion phase (after host uncordon)
# =============================================================================


@mark.p2
@mark.lab_is_simplex
def test_manual_abort_rejected_at_upgrade_complete(request: FixtureRequest) -> None:
    """Verify aborting is rejected once the upgrade reaches 'upgrade-complete'.

    Test Steps:
        - Start and drive the full upgrade through host uncordon.
        - Complete the Kubernetes upgrade (reach upgrade-complete).
        - Attempt to abort and verify it is rejected with the state-specific message.
        - Verify the upgrade is not rolled back and the target version is active.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If the abort is not rejected, or if any validation step fails.
    """
    _run_abort_scenario(request, STEP_KUBE_UPGRADE_COMPLETE)


@mark.p2
@mark.lab_is_simplex
def test_manual_abort_rejected_at_post_application_update(request: FixtureRequest) -> None:
    """Verify aborting is rejected at the 'post-updated-apps' stage.

    Test Steps:
        - Start and drive the full upgrade through host uncordon and kube-upgrade-complete.
        - Run post-application-update (reach post-updated-apps).
        - Attempt to abort and verify it is rejected with the state-specific message.
        - Verify the upgrade is not rolled back and the target version is active.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If the abort is not rejected, or if any validation step fails.
    """
    _run_abort_scenario(request, STEP_KUBE_POST_APPLICATION_UPDATE)
