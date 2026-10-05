"""
Validate combined (Platform + Kubernetes) upgrade failure injection scenarios.

These tests exercise fault injection during a combined upgrade initiated
via 'software system-deploy init' or an orchestrated sw-deploy-strategy.
The tests disrupt the control-plane upgrade phase (killing critical
processes such as etcd/kubeadm, or force-rebooting the controller) and
verify the upgrade/strategy fails gracefully. For the manual flow the
control-plane upgrade is retried and verified to succeed; for the
orchestrated flows the strategy aborts, the kube-upgrade reaches
'upgrade-aborted', and the control-plane and etcd versions are verified to
roll back to their originals.

Prerequisites:
    - Lab must be in a state where a combined upgrade can be started
      (release uploaded and available, system healthy).
    - Runs on simplex lab.
"""

from pytest import FixtureRequest, mark

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals, validate_str_contains
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.objects.swmanager_sw_deploy_strategy_create_config import SwManagerSwDeployStrategyCreateConfig
from keywords.cloud_platform.swmanager.swmanager_sw_deploy_strategy_keywords import SwManagerSwDeployStrategyKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.kubernetes.etcd_keywords import EtcdKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_keywords import KubeHostUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_list_keywords import KubeHostUpgradeListKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_fault_injection_keywords import KubeUpgradeFaultInjectionKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_keywords import KubeUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_show_keywords import KubeUpgradeShowKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from keywords.cloud_platform.upgrade.software_deploy_show_keywords import SoftwareDeployShowKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords

# The sw-deploy-strategy current-step value for the Kubernetes control-plane upgrade phase.
CONTROL_PLANE_STEP = "kube-host-upgrade-control-plane"

# The sw-deploy-strategy current-step reached once the Kubernetes control-plane
# upgrade has completed and the control-plane pods are being confirmed ready.
# Reaching this step confirms the control-plane upgrade is done.
POST_CONTROL_PLANE_STEP = "wait-kube-control-plane-pods-ready"

# sysinv log on the active controller and the marker written when the control-plane
# upgrade fails. Reading this log detects the failure without querying the Kubernetes
# API, which is unavailable while etcd is being killed. The message includes the
# target Kubernetes version, so the marker is built per test from that version.
SYSINV_LOG_PATH = "/var/log/sysinv.log"
CONTROL_PLANE_FAILURE_LOG_MARKER_TEMPLATE = "Kubernetes control-plane upgrade to version {kube_version} failed on this host"

# When etcd is killed during the orchestrated control-plane phase, the strategy
# aborts with apply-result 'failed' and an apply-reason that names the failing
# step and its underlying kube-upgrade state, e.g.
# '(kube-host-upgrade-control-plane) failed:(upgrading-first-master-failed)'.
STRATEGY_APPLY_RESULT_FAILED = "failed"
FIRST_MASTER_FAILED_REASON = "upgrading-first-master-failed"


def _get_available_release(ssh_connection: SSHConnection) -> str:
    """Resolve the first software release in the 'available' state.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        str: The first release in the 'available' state.
    """
    available_release = SoftwareListKeywords(ssh_connection).get_software_list().get_release_name_by_state("available")
    validate_not_equals(available_release, [], "At least one release in 'available' state must exist")
    return available_release[0]


def _verify_kube_and_etcd_versions_rolled_back(hostname: str, original_control_plane_version: str, original_etcd_version: str) -> None:
    """Verify the control-plane and etcd versions rolled back to their originals.

    Re-establishes a fresh SSH connection before querying, so the check remains
    valid even if the test body rebooted or swacted the active controller. Fails
    the test if either version does not match the value recorded before the upgrade.

    Args:
        hostname (str): Hostname whose control-plane version is verified.
        original_control_plane_version (str): Control-plane version recorded before the upgrade.
        original_etcd_version (str): Etcd version recorded before the upgrade.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify control-plane version rolled back to original")
    rollback_control_plane_version = KubeHostUpgradeListKeywords(ssh_connection).kube_host_upgrade_list().get_host_upgrade_by_hostname(hostname).get_control_plane_version()
    get_logger().log_info(f"Control-plane version after abort: {rollback_control_plane_version}")
    validate_equals(rollback_control_plane_version, original_control_plane_version, "Control-plane version rolled back to original")

    get_logger().log_test_case_step("Verify etcd version rolled back to original")
    rollback_etcd_version = EtcdKeywords(ssh_connection).get_etcd_version()
    get_logger().log_info(f"Etcd version after abort: {rollback_etcd_version}")
    validate_equals(rollback_etcd_version, original_etcd_version, "Etcd version rolled back to original")


def cleanup_kube_upgrade_and_system_deploy() -> None:
    """Abort and delete the Kubernetes upgrade and the software system-deploy if present.

    Idempotent teardown helper shared by the manual and orchestrated combined-upgrade
    tests. Each entity is checked for existence first, then cleaned, so a genuine
    failure of an abort/delete surfaces instead of being masked as "nothing to clean".
    A fresh SSH connection is taken so it remains valid even after a controller reboot
    or swact performed by the test body.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    usm_keywords = USMKeywords(ssh_connection)

    if kube_upgrade_show_keywords.is_kube_upgrade_in_progress():
        current_state = kube_upgrade_show_keywords.kube_upgrade_show().get_kube_upgrade_show_object().get_state()
        get_logger().log_info(f"Kubernetes upgrade present in state '{current_state}'")
        # Only abort when it is not already aborted: 'system kube-upgrade-abort'
        # returns a non-zero code if the upgrade is already in 'upgrade-aborted'.
        if current_state != "upgrade-aborted":
            get_logger().log_teardown_step("Abort Kubernetes upgrade")
            kube_upgrade_keywords.kube_upgrade_abort()
            kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-aborted", timeout=300)
        get_logger().log_teardown_step("Delete Kubernetes upgrade")
        kube_upgrade_keywords.kube_upgrade_delete()
    else:
        get_logger().log_info("No Kubernetes upgrade to clean up")

    if SoftwareDeployShowKeywords(ssh_connection).get_software_deploy_show().get_software_deploy_show() is not None:
        get_logger().log_teardown_step("Abort software deploy")
        usm_keywords.software_deploy_abort()

    get_logger().log_teardown_step("Delete system deploy if present")
    try:
        usm_keywords.system_deploy_delete()
    except (AssertionError, KeywordException) as e:
        get_logger().log_info(f"No system deploy to delete: {e}")


def cleanup_sw_deploy_strategy() -> None:
    """Abort/delete the sw-deploy-strategy, kube upgrade, and system deploy if present.

    Idempotent teardown helper shared by the orchestrated combined-upgrade tests.
    A combined (Platform + Kubernetes) orchestrated upgrade leaves three things
    behind that must all be cleaned up: the sw-deploy-strategy, the Kubernetes
    upgrade, and the software system-deploy. Deleting only the strategy leaves the
    kube upgrade and system deploy in progress, which blocks subsequent tests.

    A fresh SSH connection is taken so it remains valid even after a controller
    reboot performed by the test body. Each entity is checked for existence before
    cleanup so a genuine failure surfaces, and all three cleanups always run
    regardless of whether a strategy exists.
    """
    teardown_ssh = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_teardown_step("Delete sw-deploy-strategy if needed")
    strategy_keywords = SwManagerSwDeployStrategyKeywords(teardown_ssh)
    if strategy_keywords.check_sw_deploy_strategy_exists():
        strategy_keywords.get_sw_deploy_strategy_abort()
        strategy_keywords.wait_for_state(["aborted", "abort-failed"], timeout=300)
        strategy_keywords.get_sw_deploy_strategy_delete()
    else:
        get_logger().log_info("No sw-deploy-strategy to clean up")

    cleanup_kube_upgrade_and_system_deploy()
    AlarmListKeywords(teardown_ssh).wait_for_all_alarms_cleared()


# ==============================================================================
# Test: Kill etcd during control-plane upgrade, verify failure, then retry
# ==============================================================================


@mark.p2
@mark.lab_is_simplex
def test_combined_upgrade_kill_etcd_during_control_plane_upgrade(request: FixtureRequest) -> None:
    """Test that killing etcd during control-plane upgrade causes failure and retry succeeds.

    Initiates a combined upgrade, advances through all prerequisite steps,
    then starts the control-plane upgrade. While the control-plane upgrade
    is in progress, the etcd process is repeatedly killed to force a
    failure. After the control-plane upgrade reaches
    'upgrading-control-plane-failed', the test retries the control-plane
    upgrade and verifies it completes successfully.

    Test Steps:
        - Record control-plane and etcd versions before the upgrade
        - Initialize combined upgrade (system-deploy init + kube-upgrade-start)
        - Advance through download-images, pre-app-update, networking, storage
        - Start control-plane upgrade on the active controller
        - Kill etcd repeatedly until 'upgrading-control-plane-failed' status
        - Wait for etcd to be running again
        - Retry the control-plane upgrade
        - Wait for 'upgraded-first-master' state
        - Verify control-plane version matches target
        - Abort and cleanup the upgrade
        - Verify control-plane and etcd versions rolled back to their originals

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    target_platform_release = _get_available_release(ssh_connection)
    target_kube_version = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list().get_highest_version_by_state("available")
    usm_keywords = USMKeywords(ssh_connection)

    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_host_upgrade_keywords = KubeHostUpgradeKeywords(ssh_connection)
    kube_host_upgrade_list_keywords = KubeHostUpgradeListKeywords(ssh_connection)
    fault_injection_keywords = KubeUpgradeFaultInjectionKeywords(ssh_connection)

    request.addfinalizer(cleanup_kube_upgrade_and_system_deploy)

    get_logger().log_setup_step("Record control-plane and etcd versions before upgrade")
    setup_active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()
    original_control_plane_version = KubeHostUpgradeListKeywords(ssh_connection).kube_host_upgrade_list().get_host_upgrade_by_hostname(setup_active_controller).get_control_plane_version()
    original_etcd_version = EtcdKeywords(ssh_connection).get_etcd_version()
    get_logger().log_info(f"Versions before upgrade - control-plane: {original_control_plane_version}, etcd: {original_etcd_version}")

    get_logger().log_test_case_step(f"Initialize combined upgrade: software system-deploy init {target_platform_release} --kube-upgrade {target_kube_version}")
    usm_keywords.system_deploy_init(target_platform_release, kube_upgrade=target_kube_version)

    get_logger().log_test_case_step(f"Start Kubernetes upgrade to {target_kube_version}")
    kube_upgrade_keywords.kube_upgrade_start(target_kube_version)

    get_logger().log_test_case_step("Download images and wait for completion")
    kube_upgrade_keywords.kube_upgrade_download_images()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "downloaded-images",
        timeout=300,
        failure_states=["downloading-images-failed"],
    )

    get_logger().log_test_case_step("Pre-application-update and wait for completion")
    kube_upgrade_keywords.kube_pre_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "pre-updated-apps",
        timeout=300,
        failure_states=["pre-updating-apps-failed"],
    )

    get_logger().log_test_case_step("Networking upgrade and wait for completion")
    kube_upgrade_keywords.kube_upgrade_networking()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-networking",
        timeout=300,
        failure_states=["upgrading-networking-failed"],
    )

    get_logger().log_test_case_step("Storage upgrade and wait for completion")
    kube_upgrade_keywords.kube_upgrade_storage()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-storage",
        timeout=300,
        failure_states=["upgrading-storage-failed"],
    )

    get_logger().log_test_case_step("Get active controller hostname")
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_test_case_step(f"Start control-plane upgrade on {active_controller}")
    kube_host_upgrade_keywords.kube_host_upgrade_control_plane(active_controller)

    get_logger().log_test_case_step("Kill etcd continuously until sysinv.log reports the control-plane upgrade failure")
    # The control-plane upgrades one minor version at a time, so the failure is
    # logged against the version this host is currently upgrading to
    # (kube-host-upgrade-list 'target_version'), which may be lower than the
    # overall target_kube_version.
    step_kube_version = kube_host_upgrade_list_keywords.kube_host_upgrade_list().get_host_upgrade_by_hostname(active_controller).get_target_version()
    control_plane_failure_marker = CONTROL_PLANE_FAILURE_LOG_MARKER_TEMPLATE.format(kube_version=step_kube_version)
    fault_injection_keywords.kill_process_until_log_marker("/usr/bin/[e]tcd", SYSINV_LOG_PATH, control_plane_failure_marker, timeout=300, signal="9")
    get_logger().log_info("sysinv.log reported the control-plane upgrade failure after killing etcd")

    get_logger().log_test_case_step("Verify kube-upgrade state is 'upgrading-first-master-failed'")
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrading-first-master-failed", timeout=300)

    get_logger().log_test_case_step("Wait for alarms gone excluding 'Software release deploy in progress' and 'Kubernetes upgrade in progress'")
    AlarmListKeywords(ssh_connection).wait_for_all_alarms_cleared_excluding(["900.007", "900.023"])

    get_logger().log_test_case_step(f"Retry control-plane upgrade on {active_controller}")
    kube_host_upgrade_keywords.kube_host_upgrade_control_plane(active_controller)

    get_logger().log_test_case_step("Wait for 'upgraded-first-master' state after retry")
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-first-master",
        timeout=600,
        failure_states=["upgrading-first-master-failed"],
    )

    get_logger().log_test_case_step("Verify control-plane version matches target")
    control_plane_version = kube_host_upgrade_list_keywords.kube_host_upgrade_list().get_host_upgrade_by_hostname(active_controller).get_control_plane_version()
    validate_equals(control_plane_version, step_kube_version, "Control-plane version matches target after retry")

    get_logger().log_test_case_step("Abort and cleanup the upgrade")
    kube_upgrade_keywords.kube_upgrade_abort()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-aborted", timeout=300)
    kube_upgrade_keywords.kube_upgrade_delete()
    usm_keywords.system_deploy_delete()
    AlarmListKeywords(ssh_connection).wait_for_all_alarms_cleared()

    _verify_kube_and_etcd_versions_rolled_back(active_controller, original_control_plane_version, original_etcd_version)


# ==============================================================================
# Test: Kill etcd during orchestrated combined upgrade control-plane phase
# ==============================================================================


@mark.p2
@mark.lab_is_simplex
def test_orchestrated_combined_upgrade_kill_etcd_during_control_plane_upgrade(request: FixtureRequest) -> None:
    """Test that killing etcd during orchestrated combined upgrade causes strategy failure.

    Creates and applies a sw-deploy-strategy for a combined Platform +
    Kubernetes upgrade. Waits for the orchestration to reach the
    control-plane upgrade phase, then repeatedly kills the etcd process to
    force the strategy into a failed/aborted state. Verifies the strategy
    transitions to 'aborted' with apply-result 'failed', the kube-upgrade
    reaches 'upgrade-aborted', and the control-plane and etcd versions roll
    back to their originals.

    Test Steps:
        - Create sw-deploy-strategy with target release and kube-upgrade version
        - Wait for strategy to reach 'ready-to-apply' state
        - Apply the strategy
        - Wait for the strategy to reach 'kube-host-upgrade-control-plane' step
        - Kill etcd repeatedly until strategy reaches 'aborting'/'aborted'
        - Wait for strategy to reach 'aborted' state
        - Verify apply-result is 'failed' and apply-reason names the control-plane step
        - Wait for kube-upgrade to reach 'upgrade-aborted' state
        - Verify control-plane and etcd versions rolled back to their originals

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    target_platform_release = _get_available_release(ssh_connection)
    target_kube_version = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list().get_highest_version_by_state("available")
    sw_deploy_strategy_keywords = SwManagerSwDeployStrategyKeywords(ssh_connection)
    fault_injection_keywords = KubeUpgradeFaultInjectionKeywords(ssh_connection)

    request.addfinalizer(cleanup_sw_deploy_strategy)

    get_logger().log_setup_step("Record control-plane and etcd versions before upgrade")
    setup_active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()
    original_control_plane_version = KubeHostUpgradeListKeywords(ssh_connection).kube_host_upgrade_list().get_host_upgrade_by_hostname(setup_active_controller).get_control_plane_version()
    original_etcd_version = EtcdKeywords(ssh_connection).get_etcd_version()
    get_logger().log_info(f"Versions before upgrade - control-plane: {original_control_plane_version}, etcd: {original_etcd_version}")

    get_logger().log_test_case_step(f"Create sw-deploy-strategy for {target_platform_release} --kube-upgrade {target_kube_version}")
    create_config = SwManagerSwDeployStrategyCreateConfig(
        release=target_platform_release,
        kube_upgrade=target_kube_version,
    )
    create_result = sw_deploy_strategy_keywords.get_sw_deploy_strategy_create(create_config)
    validate_equals(create_result, True, "sw-deploy-strategy create succeeded")

    get_logger().log_test_case_step("Wait for strategy to reach 'ready-to-apply' state")
    ready_result = sw_deploy_strategy_keywords.wait_for_state(["ready-to-apply"], timeout=300)
    validate_equals(ready_result, True, "Strategy reached 'ready-to-apply' state")

    get_logger().log_test_case_step("Apply the sw-deploy-strategy")
    apply_result = sw_deploy_strategy_keywords.get_sw_deploy_strategy_apply()
    validate_equals(apply_result, True, "sw-deploy-strategy apply succeeded")

    get_logger().log_test_case_step("Wait for strategy to reach control-plane upgrade stage")
    sw_deploy_strategy_keywords.wait_for_step(CONTROL_PLANE_STEP, timeout=300)

    get_logger().log_test_case_step("Kill etcd continuously until sysinv.log reports the control-plane upgrade failure")
    # The control-plane upgrades one minor version at a time, so the failure is
    # logged against the version this host is currently upgrading to
    # (kube-host-upgrade-list 'target_version'), which may be lower than the
    # overall target_kube_version.
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()
    step_kube_version = KubeHostUpgradeListKeywords(ssh_connection).kube_host_upgrade_list().get_host_upgrade_by_hostname(active_controller).get_target_version()
    control_plane_failure_marker = CONTROL_PLANE_FAILURE_LOG_MARKER_TEMPLATE.format(kube_version=step_kube_version)
    fault_injection_keywords.kill_process_until_log_marker(
        "/usr/bin/[e]tcd",
        SYSINV_LOG_PATH,
        control_plane_failure_marker,
        timeout=300,
        signal="9",
    )
    get_logger().log_info("sysinv.log reported the control-plane upgrade failure after killing etcd")

    get_logger().log_test_case_step("Wait for strategy to reach 'aborted' state")
    aborted_result = sw_deploy_strategy_keywords.wait_for_state(["aborted"], timeout=300)
    validate_equals(aborted_result, True, "Strategy reached 'aborted' state")

    get_logger().log_test_case_step("Verify the strategy failed due to the control-plane (first-master) upgrade failure")
    strategy = sw_deploy_strategy_keywords.get_sw_deploy_strategy_show().get_swmanager_sw_deploy_strategy_show()
    validate_equals(strategy.get_apply_result(), STRATEGY_APPLY_RESULT_FAILED, "sw-deploy-strategy apply-result is 'failed'")
    validate_str_contains(strategy.get_apply_reason(), CONTROL_PLANE_STEP, "apply-reason names the control-plane upgrade step")
    validate_str_contains(strategy.get_apply_reason(), FIRST_MASTER_FAILED_REASON, "apply-reason reports the first-master upgrade failure")

    get_logger().log_test_case_step("Verify kube-upgrade state is 'upgrade-aborted'")
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-aborted", timeout=300)

    _verify_kube_and_etcd_versions_rolled_back(setup_active_controller, original_control_plane_version, original_etcd_version)


# ==============================================================================
# Test: Kill kubeadm during orchestrated combined upgrade control-plane phase
# ==============================================================================


@mark.p2
@mark.lab_is_simplex
def test_orchestrated_combined_upgrade_kill_kubeadm_during_control_plane_upgrade(request: FixtureRequest) -> None:
    """Test that killing kubeadm during orchestrated combined upgrade causes strategy failure.

    Creates and applies a sw-deploy-strategy for a combined Platform +
    Kubernetes upgrade. Waits for the orchestration to reach the
    control-plane upgrade phase, then repeatedly kills the kubeadm process to
    force the strategy into a failed/aborted state. Verifies the strategy
    transitions to 'aborted', the kube-upgrade reaches 'upgrade-aborted', and
    the control-plane and etcd versions roll back to their originals.

    Test Steps:
        - Create sw-deploy-strategy with target release and kube-upgrade version
        - Wait for strategy to reach 'ready-to-apply' state
        - Apply the strategy
        - Wait for the strategy to reach 'kube-host-upgrade-control-plane' step
        - Kill kubeadm repeatedly until strategy reaches 'aborting'/'aborted'
        - Wait for strategy to reach 'aborted' state
        - Wait for kube-upgrade to reach 'upgrade-aborted' state
        - Verify control-plane and etcd versions rolled back to their originals

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    target_platform_release = _get_available_release(ssh_connection)
    target_kube_version = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list().get_highest_version_by_state("available")
    sw_deploy_strategy_keywords = SwManagerSwDeployStrategyKeywords(ssh_connection)
    fault_injection_keywords = KubeUpgradeFaultInjectionKeywords(ssh_connection)

    request.addfinalizer(cleanup_sw_deploy_strategy)

    get_logger().log_setup_step("Record control-plane and etcd versions before upgrade")
    setup_active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()
    original_control_plane_version = KubeHostUpgradeListKeywords(ssh_connection).kube_host_upgrade_list().get_host_upgrade_by_hostname(setup_active_controller).get_control_plane_version()
    original_etcd_version = EtcdKeywords(ssh_connection).get_etcd_version()
    get_logger().log_info(f"Versions before upgrade - control-plane: {original_control_plane_version}, etcd: {original_etcd_version}")

    get_logger().log_test_case_step(f"Create sw-deploy-strategy for {target_platform_release} --kube-upgrade {target_kube_version}")
    create_config = SwManagerSwDeployStrategyCreateConfig(
        release=target_platform_release,
        kube_upgrade=target_kube_version,
    )
    create_result = sw_deploy_strategy_keywords.get_sw_deploy_strategy_create(create_config)
    validate_equals(create_result, True, "sw-deploy-strategy create succeeded")

    get_logger().log_test_case_step("Wait for strategy to reach 'ready-to-apply' state")
    ready_result = sw_deploy_strategy_keywords.wait_for_state(["ready-to-apply"], timeout=300)
    validate_equals(ready_result, True, "Strategy reached 'ready-to-apply' state")

    get_logger().log_test_case_step("Apply the sw-deploy-strategy")
    apply_result = sw_deploy_strategy_keywords.get_sw_deploy_strategy_apply()
    validate_equals(apply_result, True, "sw-deploy-strategy apply succeeded")

    get_logger().log_test_case_step("Wait for strategy to reach control-plane upgrade stage")
    sw_deploy_strategy_keywords.wait_for_step(CONTROL_PLANE_STEP, timeout=300)

    get_logger().log_test_case_step("Kill kubeadm repeatedly until strategy fails")
    fault_injection_keywords.kill_process_until_state(
        "[k]ubeadm",
        sw_deploy_strategy_keywords.get_current_state,
        ["aborting", "aborted"],
        timeout=300,
    )
    get_logger().log_info("Strategy reached aborting/aborted state after killing kubeadm")

    get_logger().log_test_case_step("Wait for strategy to reach 'aborted' state")
    aborted_result = sw_deploy_strategy_keywords.wait_for_state(["aborted"], timeout=300)
    validate_equals(aborted_result, True, "Strategy reached 'aborted' state")

    get_logger().log_test_case_step("Verify kube-upgrade state is 'upgrade-aborted'")
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-aborted", timeout=300)

    _verify_kube_and_etcd_versions_rolled_back(setup_active_controller, original_control_plane_version, original_etcd_version)


# ==============================================================================
# Test: Force reboot after orchestrated control-plane upgrade completes
# ==============================================================================


@mark.p2
@mark.lab_is_simplex
def test_orchestrated_combined_upgrade_reboot_after_control_plane_completed(request: FixtureRequest) -> None:
    """Test that force rebooting after orchestrated control-plane upgrade causes strategy failure.

    Creates and applies a sw-deploy-strategy for a combined Platform +
    Kubernetes upgrade. Waits for the orchestration to complete the
    control-plane upgrade phase (strategy advances past that step), then
    force reboots the controller. After the host comes back online,
    verifies the strategy transitions to 'aborted', clears the strategy and
    the Kubernetes upgrade and system deploy, and verifies the control-plane
    and etcd versions revert to their originals.

    Test Steps:
        - Record active controller, uptime, and control-plane and etcd versions before upgrade
        - Create sw-deploy-strategy with target release and kube-upgrade version
        - Wait for strategy to reach 'ready-to-apply' state
        - Apply the strategy
        - Wait for the strategy to reach the step after control-plane upgrade (wait-kube-control-plane-pods-ready)
        - Force reboot the active controller with 'sudo reboot -f'
        - Wait for host to come back online
        - Verify strategy reached 'aborted' state
        - Delete the aborted sw-deploy-strategy
        - Abort and delete the Kubernetes upgrade, then delete the system deploy
        - Verify control-plane and etcd versions rolled back to their originals

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    target_platform_release = _get_available_release(ssh_connection)
    target_kube_version = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list().get_highest_version_by_state("available")
    sw_deploy_strategy_keywords = SwManagerSwDeployStrategyKeywords(ssh_connection)
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    reboot_keywords = SystemHostRebootKeywords(ssh_connection)
    usm_keywords = USMKeywords(ssh_connection)
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)

    request.addfinalizer(cleanup_sw_deploy_strategy)

    get_logger().log_setup_step("Record active controller, uptime, and control-plane and etcd versions before upgrade")
    active_controller = system_host_list_keywords.get_active_controller().get_host_name()
    pre_uptime = system_host_list_keywords.get_uptime(active_controller)
    original_control_plane_version = KubeHostUpgradeListKeywords(ssh_connection).kube_host_upgrade_list().get_host_upgrade_by_hostname(active_controller).get_control_plane_version()
    original_etcd_version = EtcdKeywords(ssh_connection).get_etcd_version()
    get_logger().log_info(f"Versions before upgrade - control-plane: {original_control_plane_version}, etcd: {original_etcd_version}")

    get_logger().log_test_case_step(f"Create sw-deploy-strategy for {target_platform_release} --kube-upgrade {target_kube_version}")
    create_config = SwManagerSwDeployStrategyCreateConfig(
        release=target_platform_release,
        kube_upgrade=target_kube_version,
    )
    create_result = sw_deploy_strategy_keywords.get_sw_deploy_strategy_create(create_config)
    validate_equals(create_result, True, "sw-deploy-strategy create succeeded")

    get_logger().log_test_case_step("Wait for strategy to reach 'ready-to-apply' state")
    ready_result = sw_deploy_strategy_keywords.wait_for_state(["ready-to-apply"], timeout=300)
    validate_equals(ready_result, True, "Strategy reached 'ready-to-apply' state")

    get_logger().log_test_case_step("Apply the sw-deploy-strategy")
    apply_result = sw_deploy_strategy_keywords.get_sw_deploy_strategy_apply()
    validate_equals(apply_result, True, "sw-deploy-strategy apply succeeded")

    get_logger().log_test_case_step("Wait for strategy to finish control-plane upgrade and start upgrade")
    sw_deploy_strategy_keywords.wait_for_step(POST_CONTROL_PLANE_STEP, timeout=900)

    get_logger().log_test_case_step("Force reboot the active controller")
    reboot_keywords.host_force_reboot()

    get_logger().log_test_case_step(f"Wait for {active_controller} to come back online after reboot")
    reboot_success = SystemHostRebootKeywords(ssh_connection).wait_for_force_reboot(active_controller, pre_uptime)
    validate_equals(reboot_success, True, f"{active_controller} rebooted successfully")

    get_logger().log_test_case_step("Verify strategy reached 'aborted' state")
    sw_deploy_strategy_keywords_post = SwManagerSwDeployStrategyKeywords(ssh_connection)
    aborted_result = sw_deploy_strategy_keywords_post.wait_for_state(["aborted"], timeout=300)
    validate_equals(aborted_result, True, "Strategy reached 'aborted' state after reboot")

    get_logger().log_test_case_step("Delete sw-deploy-strategy")
    sw_deploy_strategy_keywords_post.get_sw_deploy_strategy_delete()

    get_logger().log_test_case_step("Abort Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_abort()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-aborted", timeout=300)

    get_logger().log_test_case_step("Delete Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_delete()

    get_logger().log_test_case_step("Delete system deploy")
    usm_keywords.system_deploy_delete()

    _verify_kube_and_etcd_versions_rolled_back(active_controller, original_control_plane_version, original_etcd_version)
