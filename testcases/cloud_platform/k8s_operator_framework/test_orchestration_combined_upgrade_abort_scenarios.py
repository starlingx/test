"""Validate combined (Platform & Kubernetes) sw-deploy-strategy orchestration abort scenarios.

This module creates a combined P&K ``sw-manager sw-deploy-strategy`` using valid
values (an available release plus an available target Kubernetes version), applies
it without waiting, then aborts the strategy during a specific orchestration step.
Each test aborts at a different step and verifies the strategy aborts cleanly, is
deleted, and the Kubernetes version is rolled back to the original active version.

The strategy creation mirrors
``test_sw_deploy_strategy_create_build_failed_inexistent_kube_version`` in
``test_combined_upgrade_error_scenarios.py`` but uses valid values so the strategy
builds successfully and can be applied.

Prerequisites:
- Lab must be simplex with a combined upgrade available.
- At least one release must be in the 'available' state.
- At least one Kubernetes version must be in the 'available' state.
"""

from pytest import FixtureRequest, mark

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.objects.swmanager_sw_deploy_strategy_create_config import SwManagerSwDeployStrategyCreateConfig
from keywords.cloud_platform.swmanager.swmanager_sw_deploy_strategy_keywords import SwManagerSwDeployStrategyKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_keywords import KubeUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_show_keywords import KubeUpgradeShowKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from keywords.cloud_platform.upgrade.software_deploy_show_keywords import SoftwareDeployShowKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords

# =============================================================================
# Orchestration step names (sw-deploy-strategy 'current-step' values)
# =============================================================================
# The combined P&K sw-deploy-strategy progresses through these steps. Each test
# aborts after the strategy reaches one of them. Substring matching is used when
# waiting, so these must match the 'current-step' reported by
# 'sw-manager sw-deploy-strategy show'.

STEP_KUBE_UPGRADE_DOWNLOAD_IMAGES = "kube-upgrade-download-images"
STEP_KUBE_PRE_APPLICATION_UPDATE = "kube-pre-application-update"
STEP_KUBE_UPGRADE_NETWORKING = "kube-upgrade-networking"
# The reported current-step for this stage is 'kube-host-upgrade-control-plane
# <kubernetes-version>' (e.g. 'kube-host-upgrade-control-plane v1.29.2'). The
# trailing version varies, so only the version-independent prefix is stored here
# and the substring match in SwManagerSwDeployStrategyObject.is_at_step ignores
# the version.
STEP_KUBE_HOST_UPGRADE_CONTROL_PLANE = "kube-host-upgrade-control-plane"
STEP_SW_UPGRADE_START = "start-upgrade"
STEP_SW_UPGRADE_WORKER_HOSTS = "upgrade-hosts"
STEP_SW_UPGRADE_COMPLETE = "sw-upgrade-complete"

# Strategy states.
STATE_READY_TO_APPLY = "ready-to-apply"
STATE_ABORTED = "aborted"
STATE_APPLIED = "applied"

# Default timeout (seconds) for a step to be reached.
DEFAULT_STEP_TIMEOUT = 1800

# Timeout (seconds) for the sw-upgrade-complete step to be reached (longer, as it
# follows the full worker-host upgrade).
SW_UPGRADE_COMPLETE_STEP_TIMEOUT = 3600

# Timeout (seconds) for the rollback strategy to reach the applied (complete) state.
ROLLBACK_APPLY_TIMEOUT = 3600


def _resolve_available_release(ssh_connection: SSHConnection) -> str:
    """Resolve a valid release in the 'available' state for the strategy.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        str: The first release in the 'available' state.
    """
    software_list = SoftwareListKeywords(ssh_connection).get_software_list()
    available_releases = software_list.get_release_name_by_state("available")
    validate_not_equals(available_releases, [], "At least one release in 'available' state must exist")
    release = available_releases[0]
    get_logger().log_info(f"Resolved release '{release}'")
    return release


def _resolve_target_kube_version(ssh_connection: SSHConnection) -> str:
    """Resolve the highest Kubernetes version in the 'available' state.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        str: The highest Kubernetes version in the 'available' state.
    """
    kube_version_output = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list()
    target_kube_version = kube_version_output.get_highest_version_by_state("available")
    validate_not_equals(target_kube_version, None, "A Kubernetes version in 'available' state must exist")
    get_logger().log_info(f"Resolved target Kubernetes version '{target_kube_version}'")
    return target_kube_version


def _delete_upgrade_entities(ssh_connection: SSHConnection) -> None:
    """Delete the kube-upgrade and system-deploy entities (pre-start cleanup).

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Raises:
        AssertionError: If either delete command fails.
    """
    get_logger().log_test_case_step("Delete the kube-upgrade entity (system kube-upgrade-delete)")
    KubeUpgradeKeywords(ssh_connection).kube_upgrade_delete()

    get_logger().log_test_case_step("Delete the system-deploy entity (software system-deploy delete)")
    USMKeywords(ssh_connection).system_deploy_delete()


def _perform_rollback_strategy(sw_deploy_strategy_keywords: SwManagerSwDeployStrategyKeywords) -> None:
    """Create, apply, complete, and delete a ``--rollback`` sw-deploy-strategy.

    Used once the software deploy has started (control plane already upgraded), where
    deleting the aborted strategy alone does not restore the system.

    Args:
        sw_deploy_strategy_keywords (SwManagerSwDeployStrategyKeywords): Strategy keyword instance.

    Raises:
        AssertionError: If any rollback step fails.
    """
    get_logger().log_test_case_step("Create a rollback sw-deploy-strategy (--rollback)")
    rollback_config = SwManagerSwDeployStrategyCreateConfig(release="", rollback=True)
    validate_equals(sw_deploy_strategy_keywords.get_sw_deploy_strategy_create(rollback_config), True, "Rollback strategy create command accepted")

    get_logger().log_test_case_step("Wait for the rollback strategy to build (ready-to-apply)")
    validate_equals(sw_deploy_strategy_keywords.wait_for_state([STATE_READY_TO_APPLY]), True, "Rollback strategy reached ready-to-apply state")

    get_logger().log_test_case_step("Apply the rollback sw-deploy-strategy and wait for it to complete")
    validate_equals(sw_deploy_strategy_keywords.get_sw_deploy_strategy_apply(), True, "Rollback strategy apply command accepted")
    validate_equals(sw_deploy_strategy_keywords.wait_for_state([STATE_APPLIED], timeout=ROLLBACK_APPLY_TIMEOUT), True, "Rollback strategy reached applied (complete) state")

    get_logger().log_test_case_step("Delete the rollback sw-deploy-strategy")
    validate_equals(sw_deploy_strategy_keywords.get_sw_deploy_strategy_delete(), True, "Rollback strategy deleted successfully")


def _apply_and_abort_at_step(
    request: FixtureRequest,
    ssh_connection: SSHConnection,
    sw_deploy_strategy_keywords: SwManagerSwDeployStrategyKeywords,
    step_name: str,
    timeout: int = DEFAULT_STEP_TIMEOUT,
) -> None:
    """Create and apply a combined P&K sw-deploy-strategy, then abort after a step.

    Registers a best-effort teardown, then creates the strategy with valid values,
    waits for it to build, applies it without waiting, waits for ``step_name``, aborts
    the strategy, and deletes it. Post-abort cleanup (entity deletion or a ``--rollback``
    strategy) and version verification are left to the caller, since they differ per
    abort point.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.
        ssh_connection (SSHConnection): SSH connection to the active controller.
        sw_deploy_strategy_keywords (SwManagerSwDeployStrategyKeywords): Strategy keyword instance.
        step_name (str): The orchestration step to wait for before aborting.
        timeout (int): Maximum wait time in seconds for the step to be reached.

    Raises:
        AssertionError: If the strategy fails to build, apply, or abort.
    """

    def teardown() -> None:
        """Best-effort clears the strategy and any leftover upgrade entities.

        Each entity is cleaned independently so a failure in one step (for example,
        no strategy present, which some CLIs report with a non-zero return code) does
        not prevent the remaining entities from being cleaned.
        """
        get_logger().log_teardown_step("Abort and delete the sw-deploy-strategy if present")
        try:
            if sw_deploy_strategy_keywords.check_sw_deploy_strategy_exists():
                sw_deploy_strategy_keywords.get_sw_deploy_strategy_abort()
                sw_deploy_strategy_keywords.wait_for_state([STATE_ABORTED])
                sw_deploy_strategy_keywords.get_sw_deploy_strategy_delete()
        except (KeywordException, AssertionError):
            get_logger().log_info("No sw-deploy-strategy to abort or delete")

        if KubeUpgradeShowKeywords(ssh_connection).is_kube_upgrade_in_progress():
            get_logger().log_teardown_step("Delete the kube-upgrade entity")
            KubeUpgradeKeywords(ssh_connection).kube_upgrade_delete()

        if SoftwareDeployShowKeywords(ssh_connection).get_software_deploy_show().get_software_deploy_show() is not None:
            get_logger().log_teardown_step("Delete the software-deploy entity")
            USMKeywords(ssh_connection).software_deploy_delete()

        get_logger().log_teardown_step("Delete the system-deploy entity if present")
        try:
            USMKeywords(ssh_connection).system_deploy_delete()
        except (KeywordException, AssertionError):
            get_logger().log_info("No system-deploy entity to delete")

        get_logger().log_teardown_step("Wait for alarms to clear")
        AlarmListKeywords(ssh_connection).wait_for_all_alarms_cleared()

    request.addfinalizer(teardown)

    release = _resolve_available_release(ssh_connection)
    target_kube_version = _resolve_target_kube_version(ssh_connection)

    get_logger().log_test_case_step(f"Create combined P&K sw-deploy-strategy for release '{release}' with kube-upgrade '{target_kube_version}'")
    config = SwManagerSwDeployStrategyCreateConfig(
        release=release,
        kube_upgrade=target_kube_version,
    )
    sw_deploy_strategy_keywords.get_sw_deploy_strategy_create(config)

    get_logger().log_test_case_step("Wait for the strategy to build (ready-to-apply)")
    validate_equals(sw_deploy_strategy_keywords.wait_for_state([STATE_READY_TO_APPLY]), True, "Strategy reached ready-to-apply state")

    get_logger().log_test_case_step("Apply the sw-deploy-strategy (non-blocking)")
    validate_equals(sw_deploy_strategy_keywords.get_sw_deploy_strategy_apply(), True, "Strategy apply command accepted")

    get_logger().log_test_case_step(f"Wait for the strategy to reach step '{step_name}'")
    validate_equals(sw_deploy_strategy_keywords.wait_for_step(step_name, timeout=timeout), True, f"Strategy reached step '{step_name}'")

    get_logger().log_test_case_step("Abort the sw-deploy-strategy")
    validate_equals(sw_deploy_strategy_keywords.get_sw_deploy_strategy_abort(), True, "Strategy abort command accepted")
    validate_equals(sw_deploy_strategy_keywords.wait_for_state([STATE_ABORTED]), True, "Strategy reached aborted state")

    get_logger().log_test_case_step("Delete the sw-deploy-strategy")
    validate_equals(sw_deploy_strategy_keywords.get_sw_deploy_strategy_delete(), True, "Strategy deleted successfully")


def _verify_kube_version_restored(ssh_connection: SSHConnection, original_kube_version: str) -> None:
    """Verify the active Kubernetes version matches the original.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        original_kube_version (str): The active Kubernetes version recorded before the upgrade.
    """
    get_logger().log_test_case_step(f"Verify Kubernetes version is still {original_kube_version}")
    current_active_version = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list().get_active_kubernetes_version()
    validate_equals(current_active_version, original_kube_version, "Kubernetes version remains unchanged after abort")


@mark.p2
@mark.lab_is_simplex
def test_orchestration_combined_upgrade_abort_during_download_images(request: FixtureRequest) -> None:
    """Test aborting a combined P&K sw-deploy-strategy during the download-images step.

    Creates a combined Platform + Kubernetes sw-deploy-strategy with valid values,
    applies it without waiting, aborts once it reaches the download-images step, and
    verifies cleanup. The software deploy has not started at this point, so deleting
    the kube-upgrade and system-deploy entities restores the system. Restricted to
    simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Record the active Kubernetes version before the upgrade
        - Create a combined P&K sw-deploy-strategy with valid release and kube version
        - Wait for the strategy to build (ready-to-apply)
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'kube-upgrade-download-images' step
        - Abort the strategy and wait for the aborted state
        - Delete the strategy, then clear the kube-upgrade and system-deploy entities
        - Verify the Kubernetes version is unchanged

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    sw_deploy_strategy_keywords = SwManagerSwDeployStrategyKeywords(ssh_connection)

    get_logger().log_test_case_step("Record the active Kubernetes version before the upgrade")
    original_kube_version = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list().get_active_kubernetes_version()

    _apply_and_abort_at_step(request, ssh_connection, sw_deploy_strategy_keywords, STEP_KUBE_UPGRADE_DOWNLOAD_IMAGES)

    # Pre-start: the software deploy has not started, so clearing the kube-upgrade
    # and system-deploy entities is sufficient to restore the system.
    _delete_upgrade_entities(ssh_connection)

    _verify_kube_version_restored(ssh_connection, original_kube_version)


@mark.p2
@mark.lab_is_simplex
def test_orchestration_combined_upgrade_abort_during_pre_application_update(request: FixtureRequest) -> None:
    """Test aborting a combined P&K sw-deploy-strategy during the pre-application-update step.

    Creates a combined Platform + Kubernetes sw-deploy-strategy with valid values,
    applies it without waiting, aborts once it reaches the pre-application-update step,
    and verifies cleanup. The software deploy has not started at this point, so deleting
    the kube-upgrade and system-deploy entities restores the system. Restricted to
    simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Record the active Kubernetes version before the upgrade
        - Create a combined P&K sw-deploy-strategy with valid release and kube version
        - Wait for the strategy to build (ready-to-apply)
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'kube-pre-application-update' step
        - Abort the strategy and wait for the aborted state
        - Delete the strategy, then clear the kube-upgrade and system-deploy entities
        - Verify the Kubernetes version is unchanged

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    sw_deploy_strategy_keywords = SwManagerSwDeployStrategyKeywords(ssh_connection)

    get_logger().log_test_case_step("Record the active Kubernetes version before the upgrade")
    original_kube_version = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list().get_active_kubernetes_version()

    _apply_and_abort_at_step(request, ssh_connection, sw_deploy_strategy_keywords, STEP_KUBE_PRE_APPLICATION_UPDATE)

    # Pre-start: the software deploy has not started, so clearing the kube-upgrade
    # and system-deploy entities is sufficient to restore the system.
    _delete_upgrade_entities(ssh_connection)

    _verify_kube_version_restored(ssh_connection, original_kube_version)


@mark.p2
@mark.lab_is_simplex
def test_orchestration_combined_upgrade_abort_during_networking(request: FixtureRequest) -> None:
    """Test aborting a combined P&K sw-deploy-strategy during the upgrade-networking step.

    Creates a combined Platform + Kubernetes sw-deploy-strategy with valid values,
    applies it without waiting, aborts once it reaches the upgrade-networking step, and
    verifies cleanup. The software deploy has not started at this point, so deleting the
    kube-upgrade and system-deploy entities restores the system. Restricted to simplex
    labs via the lab_is_simplex marker.

    Test Steps:
        - Record the active Kubernetes version before the upgrade
        - Create a combined P&K sw-deploy-strategy with valid release and kube version
        - Wait for the strategy to build (ready-to-apply)
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'kube-upgrade-networking' step
        - Abort the strategy and wait for the aborted state
        - Delete the strategy, then clear the kube-upgrade and system-deploy entities
        - Verify the Kubernetes version is unchanged

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    sw_deploy_strategy_keywords = SwManagerSwDeployStrategyKeywords(ssh_connection)

    get_logger().log_test_case_step("Record the active Kubernetes version before the upgrade")
    original_kube_version = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list().get_active_kubernetes_version()

    _apply_and_abort_at_step(request, ssh_connection, sw_deploy_strategy_keywords, STEP_KUBE_UPGRADE_NETWORKING)

    # Pre-start: the software deploy has not started, so clearing the kube-upgrade
    # and system-deploy entities is sufficient to restore the system.
    _delete_upgrade_entities(ssh_connection)

    _verify_kube_version_restored(ssh_connection, original_kube_version)


@mark.p2
@mark.lab_is_simplex
def test_orchestration_combined_upgrade_abort_during_control_plane(request: FixtureRequest) -> None:
    """Test aborting a combined P&K sw-deploy-strategy during the control-plane step.

    Creates a combined Platform + Kubernetes sw-deploy-strategy with valid values,
    applies it without waiting, aborts once it reaches the control-plane step, and
    verifies cleanup. The software deploy has not started at this point, so deleting the
    kube-upgrade and system-deploy entities restores the system. Restricted to simplex
    labs via the lab_is_simplex marker.

    Test Steps:
        - Record the active Kubernetes version before the upgrade
        - Create a combined P&K sw-deploy-strategy with valid release and kube version
        - Wait for the strategy to build (ready-to-apply)
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'kube-host-upgrade-control-plane' step
        - Abort the strategy and wait for the aborted state
        - Delete the strategy, then clear the kube-upgrade and system-deploy entities
        - Verify the Kubernetes version is unchanged

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    sw_deploy_strategy_keywords = SwManagerSwDeployStrategyKeywords(ssh_connection)

    get_logger().log_test_case_step("Record the active Kubernetes version before the upgrade")
    original_kube_version = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list().get_active_kubernetes_version()

    _apply_and_abort_at_step(request, ssh_connection, sw_deploy_strategy_keywords, STEP_KUBE_HOST_UPGRADE_CONTROL_PLANE)

    # Pre-start: the software deploy has not started, so clearing the kube-upgrade
    # and system-deploy entities is sufficient to restore the system.
    _delete_upgrade_entities(ssh_connection)

    _verify_kube_version_restored(ssh_connection, original_kube_version)


@mark.p2
@mark.lab_is_simplex
def test_orchestration_combined_upgrade_abort_during_sw_upgrade_start(request: FixtureRequest) -> None:
    """Test aborting a combined P&K sw-deploy-strategy during the sw-upgrade-start step.

    Creates a combined Platform + Kubernetes sw-deploy-strategy with valid values,
    applies it without waiting, aborts once it reaches the sw-upgrade-start step, then
    runs a dedicated --rollback strategy. Because the software deploy has started
    (control plane upgraded), a rollback is required to leave the system healthy.
    Restricted to simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Record the active Kubernetes version before the upgrade
        - Create a combined P&K sw-deploy-strategy with valid release and kube version
        - Wait for the strategy to build (ready-to-apply)
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'sw-upgrade-start' step
        - Abort the strategy and wait for the aborted state
        - Delete the strategy, then create, apply, complete, and delete a --rollback strategy
        - Verify the Kubernetes version is rolled back to the original

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    sw_deploy_strategy_keywords = SwManagerSwDeployStrategyKeywords(ssh_connection)

    get_logger().log_test_case_step("Record the active Kubernetes version before the upgrade")
    original_kube_version = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list().get_active_kubernetes_version()

    _apply_and_abort_at_step(request, ssh_connection, sw_deploy_strategy_keywords, STEP_SW_UPGRADE_START)

    # sw-upgrade-start: the software deploy has started (control plane upgraded), so a
    # dedicated --rollback strategy is run to restore the system to a healthy state.
    _perform_rollback_strategy(sw_deploy_strategy_keywords)

    _verify_kube_version_restored(ssh_connection, original_kube_version)


@mark.p2
@mark.lab_is_simplex
def test_orchestration_combined_upgrade_abort_during_sw_upgrade_worker_hosts(request: FixtureRequest) -> None:
    """Test aborting a combined P&K sw-deploy-strategy during the sw-upgrade-worker-hosts step.

    Creates a combined Platform + Kubernetes sw-deploy-strategy with valid values,
    applies it without waiting, aborts once it reaches the sw-upgrade-worker-hosts step,
    then runs a dedicated --rollback strategy that fully restores the system (no entity
    cleanup needed). Restricted to simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Record the active Kubernetes version before the upgrade
        - Create a combined P&K sw-deploy-strategy with valid release and kube version
        - Wait for the strategy to build (ready-to-apply)
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'sw-upgrade-worker-hosts' step
        - Abort the strategy and wait for the aborted state
        - Delete the strategy, then create, apply, complete, and delete a --rollback strategy
        - Verify the Kubernetes version is rolled back to the original

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    sw_deploy_strategy_keywords = SwManagerSwDeployStrategyKeywords(ssh_connection)

    get_logger().log_test_case_step("Record the active Kubernetes version before the upgrade")
    original_kube_version = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list().get_active_kubernetes_version()

    _apply_and_abort_at_step(request, ssh_connection, sw_deploy_strategy_keywords, STEP_SW_UPGRADE_WORKER_HOSTS)

    # sw-upgrade-worker-hosts: run a dedicated --rollback strategy that fully restores
    # the system; no entity cleanup is needed.
    _perform_rollback_strategy(sw_deploy_strategy_keywords)

    _verify_kube_version_restored(ssh_connection, original_kube_version)


@mark.p2
@mark.lab_is_simplex
def test_orchestration_combined_upgrade_abort_after_sw_upgrade_complete(request: FixtureRequest) -> None:
    """Test aborting a combined P&K sw-deploy-strategy after the sw-upgrade-complete step.

    Creates a combined Platform + Kubernetes sw-deploy-strategy with valid values,
    applies it without waiting, aborts once it reaches the sw-upgrade-complete step,
    then runs a dedicated --rollback strategy that fully restores the system (no entity
    cleanup needed). Restricted to simplex labs via the lab_is_simplex marker.

    Test Steps:
        - Record the active Kubernetes version before the upgrade
        - Create a combined P&K sw-deploy-strategy with valid release and kube version
        - Wait for the strategy to build (ready-to-apply)
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'sw-upgrade-complete' step
        - Abort the strategy and wait for the aborted state
        - Delete the strategy, then create, apply, complete, and delete a --rollback strategy
        - Verify the Kubernetes version is rolled back to the original

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    sw_deploy_strategy_keywords = SwManagerSwDeployStrategyKeywords(ssh_connection)

    get_logger().log_test_case_step("Record the active Kubernetes version before the upgrade")
    original_kube_version = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list().get_active_kubernetes_version()

    _apply_and_abort_at_step(request, ssh_connection, sw_deploy_strategy_keywords, STEP_SW_UPGRADE_COMPLETE, timeout=SW_UPGRADE_COMPLETE_STEP_TIMEOUT)

    # sw-upgrade-complete: run a dedicated --rollback strategy that fully restores
    # the system; no entity cleanup is needed.
    _perform_rollback_strategy(sw_deploy_strategy_keywords)

    _verify_kube_version_restored(ssh_connection, original_kube_version)
