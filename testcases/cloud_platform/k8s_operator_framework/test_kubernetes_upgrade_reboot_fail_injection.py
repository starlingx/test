"""
Validate Kubernetes upgrade reboot scenarios.

Prerequisites
- Need to be run on lab with n-1 kubernetes version
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_list_contains, validate_not_none, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.swmanager_kube_upgrade_strategy_keywords import SwManagerKubeUpgradeStrategyKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_keywords import KubeHostUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_list_keywords import KubeHostUpgradeListKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_keywords import KubeUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_show_keywords import KubeUpgradeShowKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords


def _check_apply_failed(kube_strategy_keywords: SwManagerKubeUpgradeStrategyKeywords) -> bool:
    """Check if the orchestration strategy has reached apply-failed state.

    Args:
        kube_strategy_keywords (SwManagerKubeUpgradeStrategyKeywords): Keywords for sw-manager kube-upgrade-strategy commands.

    Returns:
        bool: True if the strategy apply result is 'failed'.
    """
    try:
        strategy_output = kube_strategy_keywords.show_kube_upgrade_strategy()
        strategy_obj = strategy_output.get_swmanager_kube_upgrade_strategy_show()
        state = strategy_obj.get_apply_result()
        get_logger().log_info(f"Current strategy apply result: {state}")
        return state in ("failed", "timed-out")
    except Exception:
        get_logger().log_info("sw-manager command failed during polling, retrying")
        return False


def _reboot_during_kube_upgrade_step(request: FixtureRequest, step_name: str, expected_failure_reason: str) -> None:
    """Reboot the active controller during a specific kube upgrade step and verify failure.

    Test Steps:
        - Validate active and available Kubernetes versions
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the specified upgrade phase
        - Get host uptime before reboot
        - Force reboot the active controller
        - Wait for host to come back online after reboot
        - Verify the orchestration strategy reached apply-failed state
        - Verify apply-reason contains the expected failure reason
        - Cleanup: abort upgrade, delete strategy

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.
        step_name (str): The orchestration step to wait for before rebooting.
        expected_failure_reason (str): Expected substring in the apply-reason after failure.
    """
    lab_connection_keywords = LabConnectionKeywords()
    ssh_connection = lab_connection_keywords.get_active_controller_ssh()

    kube_strategy_keywords = SwManagerKubeUpgradeStrategyKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    reboot_keywords = SystemHostRebootKeywords(ssh_connection)

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    get_logger().log_test_case_step("Validate active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")

    target_version = kubernetes_upgrade_config.resolve_target_version(available_kube_versions)
    get_logger().log_info(f"Resolved target Kubernetes version: {target_version}")
    validate_list_contains(target_version, available_kube_versions, "Target version is in available list")

    get_logger().log_test_case_step(f"Create Kubernetes upgrade strategy for version {target_version}")
    create_output = kube_strategy_keywords.create_sw_manager_kube_upgrade_strategy(target_kube_version=target_version)
    validate_equals(create_output.get_state(), "ready-to-apply", "Strategy is ready to apply")

    get_logger().log_test_case_step("Get host uptime before reboot")
    host_name = system_host_list_keywords.get_active_controller().get_host_name()
    pre_uptime = system_host_list_keywords.get_uptime(host_name)

    get_logger().log_test_case_step("Apply Kubernetes upgrade strategy (non-blocking)")
    kube_strategy_keywords.apply_kube_upgrade_strategy_without_waiting()

    def teardown() -> None:
        """Cleanup orchestration strategy and kubernetes upgrade."""
        get_logger().log_teardown_step("Cleanup orchestration strategy and kubernetes upgrade")
        try:
            teardown_ssh = lab_connection_keywords.get_active_controller_ssh()
            teardown_strategy_keywords = SwManagerKubeUpgradeStrategyKeywords(teardown_ssh)
            teardown_strategy_keywords.abort_kube_upgrade_strategy()
        except Exception:
            get_logger().log_info("No strategy to abort")
        try:
            teardown_strategy_keywords.wait_for_aborted()
            teardown_strategy_keywords.delete_kube_upgrade_strategy()
        except Exception:
            get_logger().log_info("No strategy to delete")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Wait for strategy to reach {step_name} phase")
    kube_strategy_keywords.wait_for_kube_upgrade_step(step_name, timeout=1200)

    get_logger().log_test_case_step("Force reboot the active controller")
    reboot_keywords.host_force_reboot()

    get_logger().log_test_case_step(f"Waiting for {host_name} to come back online after reboot")
    reboot_success = SystemHostRebootKeywords(ssh_connection).wait_for_force_reboot(host_name, pre_uptime)
    validate_equals(reboot_success, True, f"{host_name} should reboot successfully")

    get_logger().log_test_case_step("Verify orchestration strategy reached apply-failed state")
    kube_strategy_keywords_post = SwManagerKubeUpgradeStrategyKeywords(ssh_connection)
    validate_equals_with_retry(lambda: _check_apply_failed(kube_strategy_keywords_post), True, "Orchestration strategy reached apply-failed after reboot", timeout=600, polling_sleep_time=30)

    get_logger().log_test_case_step(f"Verify apply-reason contains {expected_failure_reason}")
    strategy_obj = kube_strategy_keywords_post.show_kube_upgrade_strategy().get_swmanager_kube_upgrade_strategy_show()
    apply_reason = strategy_obj.get_apply_reason()
    validate_str_contains(apply_reason, expected_failure_reason, f"Apply reason indicates {expected_failure_reason}")


def test_kube_upgrade_fails_on_download_images_reboot(request: FixtureRequest) -> None:
    """Test that rebooting the active controller during image download fails orchestration.

    Test Steps:
        - Validate active and available Kubernetes versions
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the downloading-images phase
        - Force reboot the active controller
        - Wait for host to come back online after reboot
        - Verify the orchestration strategy is in apply-failed state
        - Verify apply-reason contains downloading-images-failed
        - Cleanup: abort upgrade, delete strategy

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _reboot_during_kube_upgrade_step(request, "kube-upgrade-download-images", "downloading-images-failed")


def test_kube_upgrade_fails_on_upgrade_networking_reboot(request: FixtureRequest) -> None:
    """Test that rebooting the active controller during networking upgrade fails orchestration.

    Test Steps:
        - Validate active and available Kubernetes versions
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the upgrade-networking phase
        - Force reboot the active controller
        - Wait for host to come back online after reboot
        - Verify the orchestration strategy is in apply-failed state
        - Verify apply-reason contains upgrading-networking-failed
        - Cleanup: abort upgrade, delete strategy

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _reboot_during_kube_upgrade_step(request, "kube-upgrade-networking", "upgrading-networking-failed")


def test_kube_upgrade_fails_on_upgrade_control_plane_reboot(request: FixtureRequest) -> None:
    """Test that rebooting the active controller during control-plane upgrade fails orchestration.

    Test Steps:
        - Validate active and available Kubernetes versions
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the control-plane upgrade phase
        - Force reboot the active controller
        - Wait for host to come back online after reboot
        - Verify the orchestration strategy is in apply-failed state
        - Verify apply-reason contains upgrading-first-master-failed
        - Cleanup: abort upgrade, delete strategy

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _reboot_during_kube_upgrade_step(request, "kube-host-upgrade-control-plane", "upgrading-first-master-failed")


@mark.lab_is_simplex
def test_kube_upgrade_fails_on_upgrade_kubelet_reboot_sx(request: FixtureRequest) -> None:
    """Test that rebooting during kubelet upgrade fails the upgrade.

    Upgrades control-plane on active controller, initiates kubelet upgrade
    directly (no lock needed), and reboots the active controller.

    Test Steps:
        - Start manual kubernetes upgrade to target version
        - Download images, pre-application-update, networking, storage
        - Upgrade control-plane
        - Initiate kubelet upgrade on target host
        - Force reboot the target host
        - Wait for host to come back online after reboot
        - Verify kube-host-upgrade-list status indicates failure
        - Cleanup: abort and delete upgrade

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    lab_connection_keywords = LabConnectionKeywords()
    ssh_connection = lab_connection_keywords.get_active_controller_ssh()

    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_host_upgrade_keywords = KubeHostUpgradeKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    get_logger().log_test_case_step("Validate active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")

    target_version = kubernetes_upgrade_config.resolve_target_version(available_kube_versions)
    validate_list_contains(target_version, available_kube_versions, "Target version is in available list")

    get_logger().log_test_case_step(f"Start Kubernetes upgrade to {target_version}")
    start_output = kube_upgrade_keywords.kube_upgrade_start(target_version)
    validate_equals(start_output.get_kube_upgrade_show_object().get_state(), "upgrade-started", "Upgrade started")

    def teardown() -> None:
        """Cleanup kubernetes upgrade if still in progress."""
        get_logger().log_teardown_step("Abort and delete kubernetes upgrade if needed")
        try:
            kube_upgrade_keywords.kube_upgrade_abort()
            kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-aborted", timeout=600)
            kube_upgrade_keywords.kube_upgrade_delete()
        except Exception:
            get_logger().log_info("No kubernetes upgrade to clean up")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Download Kubernetes images")
    kube_upgrade_keywords.kube_upgrade_download_images()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("downloaded-images", timeout=600, failure_states=["downloading-images-failed"])

    get_logger().log_test_case_step("Run pre-application-update")
    kube_upgrade_keywords.kube_pre_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("pre-updated-apps", timeout=600, failure_states=["pre-updating-apps-failed"])

    get_logger().log_test_case_step("Upgrade networking")
    kube_upgrade_keywords.kube_upgrade_networking()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgraded-networking", timeout=600, failure_states=["upgrading-networking-failed"])

    get_logger().log_test_case_step("Upgrade storage")
    kube_upgrade_keywords.kube_upgrade_storage()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgraded-storage", timeout=600, failure_states=["upgrading-storage-failed"])

    active_hostname = system_host_list_keywords.get_active_controller().get_host_name()

    get_logger().log_test_case_step(f"Upgrade control-plane on {active_hostname}")
    kube_host_upgrade_keywords.kube_host_upgrade_control_plane(active_hostname)
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgraded-first-master", timeout=600, failure_states=["upgrading-first-master-failed"])

    get_logger().log_test_case_step(f"Get {active_hostname} uptime before reboot")
    pre_uptime = system_host_list_keywords.get_uptime(active_hostname)

    get_logger().log_test_case_step(f"Initiate kubelet upgrade on {active_hostname}")
    kube_host_upgrade_keywords.kube_host_upgrade_kubelet(active_hostname)

    get_logger().log_test_case_step(f"Force reboot {active_hostname}")
    SystemHostRebootKeywords(ssh_connection).host_force_reboot()

    get_logger().log_test_case_step(f"Waiting for {active_hostname} to come back online after reboot")
    reboot_success = SystemHostRebootKeywords(ssh_connection).wait_for_force_reboot(active_hostname, pre_uptime)
    validate_equals(reboot_success, True, f"{active_hostname} should reboot successfully")

    get_logger().log_test_case_step("Verify kubelet upgrade failed via kube-host-upgrade-list")
    post_ssh = lab_connection_keywords.get_active_controller_ssh()
    post_host_upgrade_list_keywords = KubeHostUpgradeListKeywords(post_ssh)

    def _check_kubelet_failed() -> bool:
        try:
            host_upgrade = post_host_upgrade_list_keywords.kube_host_upgrade_list().get_host_upgrade_by_hostname(active_hostname)
            status = host_upgrade.get_status()
            get_logger().log_info(f"Host {active_hostname} upgrade status: {status}")
            return "failed" in status
        except Exception:
            return False

    validate_equals_with_retry(_check_kubelet_failed, True, f"Host {active_hostname} upgrade status indicates kubelet failed", timeout=600, polling_sleep_time=30)


@mark.lab_has_standby_controller
def test_kube_upgrade_fails_on_upgrade_kubelet_reboot_multi_node(request: FixtureRequest) -> None:
    """Test that rebooting during kubelet upgrade fails the upgrade.

    Upgrades control-plane on both controllers, locks the standby
    controller, initiates kubelet upgrade on it, and reboots the standby controller.

    Test Steps:
        - Start manual kubernetes upgrade to target version
        - Download images, pre-application-update, networking, storage
        - Upgrade control-plane (standby then active)
        - Lock standby controller
        - Initiate kubelet upgrade on target host
        - Force reboot the target host
        - Wait for host to come back online after reboot
        - Verify kube-host-upgrade-list status indicates failure
        - Cleanup: abort and delete upgrade

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    lab_connection_keywords = LabConnectionKeywords()
    ssh_connection = lab_connection_keywords.get_active_controller_ssh()

    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_host_upgrade_keywords = KubeHostUpgradeKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    system_host_lock_keywords = SystemHostLockKeywords(ssh_connection)

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    get_logger().log_test_case_step("Validate active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")

    target_version = kubernetes_upgrade_config.resolve_target_version(available_kube_versions)
    validate_list_contains(target_version, available_kube_versions, "Target version is in available list")

    get_logger().log_test_case_step(f"Start Kubernetes upgrade to {target_version}")
    start_output = kube_upgrade_keywords.kube_upgrade_start(target_version)
    validate_equals(start_output.get_kube_upgrade_show_object().get_state(), "upgrade-started", "Upgrade started")

    standby_hostname = system_host_list_keywords.get_standby_controller().get_host_name()

    def teardown() -> None:
        """Cleanup kubernetes upgrade and unlock standby controller if needed."""
        get_logger().log_teardown_step("Unlock standby controller and delete kubernetes upgrade if needed")
        try:
            teardown_ssh = lab_connection_keywords.get_active_controller_ssh()
            teardown_lock_keywords = SystemHostLockKeywords(teardown_ssh)
            if teardown_lock_keywords.is_host_locked(standby_hostname):
                teardown_lock_keywords.unlock_host(standby_hostname)
        except Exception:
            get_logger().log_info("Could not unlock standby controller")
        try:
            teardown_ssh = lab_connection_keywords.get_active_controller_ssh()
            KubeUpgradeKeywords(teardown_ssh).kube_upgrade_delete()
        except Exception:
            get_logger().log_info("No kubernetes upgrade to delete")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Download Kubernetes images")
    kube_upgrade_keywords.kube_upgrade_download_images()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("downloaded-images", timeout=600, failure_states=["downloading-images-failed"])

    get_logger().log_test_case_step("Run pre-application-update")
    kube_upgrade_keywords.kube_pre_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("pre-updated-apps", timeout=600, failure_states=["pre-updating-apps-failed"])

    get_logger().log_test_case_step("Upgrade networking")
    kube_upgrade_keywords.kube_upgrade_networking()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgraded-networking", timeout=600, failure_states=["upgrading-networking-failed"])

    get_logger().log_test_case_step("Upgrade storage")
    kube_upgrade_keywords.kube_upgrade_storage()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgraded-storage", timeout=600, failure_states=["upgrading-storage-failed"])

    active_hostname = system_host_list_keywords.get_active_controller().get_host_name()

    get_logger().log_test_case_step(f"Upgrade control-plane on standby {standby_hostname}")
    kube_host_upgrade_keywords.kube_host_upgrade_control_plane(standby_hostname)
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgraded-first-master", timeout=600, failure_states=["upgrading-first-master-failed"])

    get_logger().log_test_case_step(f"Upgrade control-plane on active {active_hostname}")
    kube_host_upgrade_keywords.kube_host_upgrade_control_plane(active_hostname)
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgraded-second-master", timeout=600, failure_states=["upgrading-second-master-failed"])

    get_logger().log_test_case_step(f"Lock standby controller {standby_hostname}")
    system_host_lock_keywords.lock_host(standby_hostname)

    get_logger().log_test_case_step(f"Get {standby_hostname} uptime before reboot")
    pre_uptime = system_host_list_keywords.get_uptime(standby_hostname)
    standby_ssh = lab_connection_keywords.get_standby_controller_ssh()

    get_logger().log_test_case_step(f"Initiate kubelet upgrade on {standby_hostname}")
    kube_host_upgrade_keywords.kube_host_upgrade_kubelet(standby_hostname)

    get_logger().log_test_case_step(f"Force reboot {standby_hostname}")
    SystemHostRebootKeywords(standby_ssh).host_force_reboot()

    get_logger().log_test_case_step(f"Waiting for {standby_hostname} to come back online after reboot")
    reboot_success = SystemHostRebootKeywords(ssh_connection).wait_for_reboot(standby_hostname, pre_uptime)
    validate_equals(reboot_success, True, f"{standby_hostname} should reboot successfully")

    get_logger().log_test_case_step("Verify kubelet upgrade failed via kube-host-upgrade-list")
    post_ssh = lab_connection_keywords.get_active_controller_ssh()
    post_host_upgrade_list_keywords = KubeHostUpgradeListKeywords(post_ssh)

    def _check_kubelet_failed() -> bool:
        try:
            host_upgrade = post_host_upgrade_list_keywords.kube_host_upgrade_list().get_host_upgrade_by_hostname(standby_hostname)
            status = host_upgrade.get_status()
            get_logger().log_info(f"Host {standby_hostname} upgrade status: {status}")
            return "failed" in status
        except Exception:
            return False

    validate_equals_with_retry(_check_kubelet_failed, True, f"Host {standby_hostname} upgrade status indicates kubelet failed", timeout=600, polling_sleep_time=30)
