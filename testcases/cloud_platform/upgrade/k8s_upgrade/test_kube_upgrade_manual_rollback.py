from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_list_contains, validate_not_none
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.healthquery.system_health_query_keywords import SystemHealthQueryKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_keywords import KubeHostUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_list_keywords import KubeHostUpgradeListKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_keywords import KubeUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_show_keywords import KubeUpgradeShowKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_utils import build_control_plane_batches
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords


@mark.lab_is_simplex
def test_kubernetes_upgrade_rollback_after_control_plane_simplex(request: FixtureRequest) -> None:
    """Test Kubernetes upgrade rollback after control-plane upgrade on a simplex lab.

    Starts a Kubernetes upgrade, upgrades the control-plane for the first
    version only, then aborts and deletes the upgrade. Verifies the active
    version reverts to the original. Then performs a full manual upgrade
    to the target version to confirm the system is still upgradeable.

    Test Steps:
        - Validate system health and available Kubernetes versions
        - Start upgrade, download images, pre-app-update, networking, storage, cordon
        - Upgrade control-plane for the first version only
        - Abort the upgrade and delete it
        - Verify the active version is the original version
        - Perform a full manual upgrade to the target version
        - Verify the target version is active on host

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_host_upgrade_keywords = KubeHostUpgradeKeywords(ssh_connection)
    kube_host_upgrade_list_keywords = KubeHostUpgradeListKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)

    k8s_config = ConfigurationManager.get_k8s_config()
    target_version = k8s_config.get_k8_target_version()

    def teardown() -> None:
        """Cleanup kubernetes upgrade if still in progress."""
        get_logger().log_teardown_step("Abort and delete kubernetes upgrade if needed")
        try:
            kube_upgrade_keywords.kube_upgrade_abort()
            kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-aborted", timeout=300)
            kube_upgrade_keywords.kube_upgrade_delete()
        except Exception:
            get_logger().log_info("No kubernetes upgrade to clean up")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Check if the system is healthy for Kubernetes upgrade")
    SystemHealthQueryKeywords(ssh_connection).is_system_healthy_for_kube_upgrade()

    get_logger().log_test_case_step("Validate active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")
    validate_list_contains(target_version, available_kube_versions, "Target version is in available list")

    original_version = active_kube_version

    get_logger().log_test_case_step(f"Start Kubernetes upgrade to {target_version}")
    start_output = kube_upgrade_keywords.kube_upgrade_start(target_version)
    validate_equals(start_output.get_kube_upgrade_show_object().get_state(), "upgrade-started", "Upgrade started")

    get_logger().log_test_case_step("Download Kubernetes images")
    kube_upgrade_keywords.kube_upgrade_download_images()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "downloaded-images",
        timeout=600,
        failure_states=["downloading-images-failed"],
    )

    get_logger().log_test_case_step("Run pre-application-update")
    kube_upgrade_keywords.kube_pre_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "pre-updated-apps",
        timeout=600,
        failure_states=["pre-updating-apps-failed"],
    )

    get_logger().log_test_case_step("Upgrade networking")
    kube_upgrade_keywords.kube_upgrade_networking()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-networking",
        timeout=600,
        failure_states=["upgrading-networking-failed"],
    )

    get_logger().log_test_case_step("Upgrade storage")
    kube_upgrade_keywords.kube_upgrade_storage()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-storage",
        timeout=600,
        failure_states=["upgrading-storage-failed"],
    )

    get_logger().log_test_case_step("Host cordon")
    kube_upgrade_keywords.kube_host_cordon(host)
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "cordon-complete",
        timeout=600,
        failure_states=["cordon-failed"],
    )

    get_logger().log_test_case_step("Upgrade control-plane for first version only")
    kube_host_upgrade_keywords.kube_host_upgrade_control_plane(host)
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-first-master",
        timeout=600,
        failure_states=["upgrading-first-master-failed"],
    )

    get_logger().log_test_case_step("Abort the Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_abort()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-aborted", timeout=600)

    get_logger().log_test_case_step("Delete the aborted Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_delete()

    get_logger().log_test_case_step(f"Verify active version reverted to {original_version}")
    current_version = system_kube_keywords.get_system_kube_version_list().get_active_kubernetes_version()
    validate_equals(current_version, original_version, "Active version reverted to original after abort")

    get_logger().log_test_case_step("Check system health before retry upgrade")
    alarm_list_keywords = AlarmListKeywords(ssh_connection)
    alarm_list_keywords.wait_for_all_alarms_cleared()
    SystemHealthQueryKeywords(ssh_connection).is_system_healthy_for_kube_upgrade()

    get_logger().log_test_case_step(f"Start Kubernetes upgrade to {target_version}")
    start_output = kube_upgrade_keywords.kube_upgrade_start(target_version, force=True)
    validate_equals(start_output.get_kube_upgrade_show_object().get_state(), "upgrade-started", "Upgrade started")

    get_logger().log_test_case_step("Download Kubernetes images")
    kube_upgrade_keywords.kube_upgrade_download_images()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "downloaded-images",
        timeout=600,
        failure_states=["downloading-images-failed"],
    )

    get_logger().log_test_case_step("Run pre-application-update")
    kube_upgrade_keywords.kube_pre_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "pre-updated-apps",
        timeout=600,
        failure_states=["pre-updating-apps-failed"],
    )

    get_logger().log_test_case_step("Upgrade networking")
    kube_upgrade_keywords.kube_upgrade_networking()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-networking",
        timeout=600,
        failure_states=["upgrading-networking-failed"],
    )

    get_logger().log_test_case_step("Upgrade storage")
    kube_upgrade_keywords.kube_upgrade_storage()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-storage",
        timeout=600,
        failure_states=["upgrading-storage-failed"],
    )

    get_logger().log_test_case_step("Host cordon")
    kube_upgrade_keywords.kube_host_cordon(host)
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "cordon-complete",
        timeout=600,
        failure_states=["cordon-failed"],
    )

    all_versions = available_kube_versions + [original_version]
    batches = build_control_plane_batches(original_version, target_version, all_versions)
    get_logger().log_info(f"Control-plane upgrade batches: {batches}")

    for batch_num, batch in enumerate(batches, 1):
        for version in batch:
            get_logger().log_test_case_step(f"Upgrade control-plane to {version} (batch {batch_num}/{len(batches)})")
            kube_host_upgrade_keywords.kube_host_upgrade_control_plane(host)
            kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
                "upgraded-first-master",
                timeout=600,
                failure_states=["upgrading-first-master-failed"],
            )

        get_logger().log_test_case_step(f"Upgrade kubelet (batch {batch_num}/{len(batches)})")
        kube_host_upgrade_keywords.kube_host_upgrade_kubelet(host)
        kube_host_upgrade_list_keywords.wait_for_host_upgrade_status(
            host,
            "upgraded-kubelet",
            timeout=600,
            failure_statuses=["upgrading-kubelets-failed"],
        )

    get_logger().log_test_case_step("Host uncordon")
    kube_upgrade_keywords.kube_host_uncordon(host)
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "uncordon-complete",
        timeout=600,
        failure_states=["uncordon-failed"],
    )

    get_logger().log_test_case_step("Complete Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_complete()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-complete", timeout=300)

    get_logger().log_test_case_step("Run post-application-update")
    kube_upgrade_keywords.kube_post_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "post-updated-apps",
        timeout=600,
        failure_states=["post-updating-apps-failed"],
    )

    get_logger().log_test_case_step("Delete Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_delete()

    get_logger().log_test_case_step(f"Verify target version {target_version} is active")
    active_version = system_kube_keywords.get_system_kube_version_list().get_active_kubernetes_version()
    validate_equals(active_version, target_version, "Target version is now active")

    get_logger().log_test_case_step("Verify all hosts upgraded via kube-host-upgrade-list")
    host_upgrade_list = kube_host_upgrade_list_keywords.kube_host_upgrade_list()
    host_upgrade = host_upgrade_list.get_host_upgrade_by_hostname(host)
    validate_equals(host_upgrade.get_control_plane_version(), target_version, f"{host} control-plane upgraded")
    validate_equals(host_upgrade.get_kubelet_version(), target_version, f"{host} kubelet upgraded")
