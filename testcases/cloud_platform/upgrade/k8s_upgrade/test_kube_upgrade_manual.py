from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_list_contains, validate_not_none
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.healthquery.system_health_query_keywords import SystemHealthQueryKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_keywords import KubeHostUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_list_keywords import KubeHostUpgradeListKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_keywords import KubeUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_show_keywords import KubeUpgradeShowKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_utils import build_control_plane_batches
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords


@mark.lab_is_simplex
def test_kubernetes_manual_upgrade_simplex(request: FixtureRequest) -> None:
    """Test manual Kubernetes upgrade on a simplex lab.

    Performs a full manual Kubernetes upgrade by executing each upgrade
    step individually: start, download images, pre-application-update,
    networking, storage, control-plane and kubelet upgrades per host,
    post-application-update, complete, and delete.

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

    all_versions = available_kube_versions + [active_kube_version]
    batches = build_control_plane_batches(active_kube_version, target_version, all_versions)
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

    get_logger().log_test_case_step("Verify host upgraded via kube-host-upgrade-list")
    host_upgrade_list = kube_host_upgrade_list_keywords.kube_host_upgrade_list()
    host_upgrade = host_upgrade_list.get_host_upgrade_by_hostname(host)
    validate_equals(host_upgrade.get_control_plane_version(), target_version, f"{host} control-plane upgraded")
    validate_equals(host_upgrade.get_kubelet_version(), target_version, f"{host} kubelet upgraded")


@mark.lab_has_standby_controller
def test_kubernetes_manual_upgrade_multi_node(request: FixtureRequest) -> None:
    """Test manual Kubernetes upgrade on multi node lab.

    Performs a full manual Kubernetes upgrade by executing each upgrade
    step individually: start, download images, pre-application-update,
    networking, storage, control-plane and kubelet upgrades per host,
    post-application-update, complete, and delete.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_host_upgrade_keywords = KubeHostUpgradeKeywords(ssh_connection)
    kube_host_upgrade_list_keywords = KubeHostUpgradeListKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    system_host_lock_unlock_keywords = SystemHostLockKeywords(ssh_connection)

    k8s_config = ConfigurationManager.get_k8s_config()
    target_version = k8s_config.get_k8_target_version()

    get_logger().log_test_case_step("Check if the system is healthy for Kubernetes upgrade")
    SystemHealthQueryKeywords(ssh_connection).is_system_healthy_for_kube_upgrade()
    get_logger().log_test_case_step("Validate active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")
    validate_list_contains(target_version, available_kube_versions, "Target version is in available list")

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

    all_versions = available_kube_versions + [active_kube_version]
    batches = build_control_plane_batches(active_kube_version, target_version, all_versions)
    get_logger().log_info(f"Control-plane upgrade batches: {batches}")

    standby_controller = system_host_list_keywords.get_standby_controller()
    standby_hostname = standby_controller.get_host_name()
    active_controller = system_host_list_keywords.get_active_controller()
    active_hostname = active_controller.get_host_name()

    for batch_num, batch in enumerate(batches, 1):
        for version in batch:
            get_logger().log_test_case_step(f"Upgrade first control-plane to {version} (batch {batch_num}/{len(batches)})")
            get_logger().log_info(f"Upgrading control-plane on {standby_hostname}")
            kube_host_upgrade_keywords.kube_host_upgrade_control_plane(standby_hostname)
            kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
                "upgraded-first-master",
                timeout=600,
                failure_states=["upgrading-first-master-failed"],
            )

            get_logger().log_test_case_step(f"Upgrade second control-plane to {version} (batch {batch_num}/{len(batches)})")
            get_logger().log_info(f"Upgrading control-plane on {active_hostname}")
            kube_host_upgrade_keywords.kube_host_upgrade_control_plane(active_hostname)
            kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
                "upgraded-second-master",
                timeout=600,
                failure_states=["upgrading-second-master-failed"],
            )

        get_logger().log_test_case_step(f"Upgrade kubelet on controller {standby_hostname} (batch {batch_num}/{len(batches)})")
        get_logger().log_info(f"Locking node {standby_hostname}")
        system_host_lock_unlock_keywords.lock_host(standby_hostname)
        kube_host_upgrade_keywords.kube_host_upgrade_kubelet(standby_hostname)
        kube_host_upgrade_list_keywords.wait_for_host_upgrade_status(
            standby_hostname,
            "upgraded-kubelet",
            timeout=600,
            failure_statuses=["upgrading-kubelets-failed"],
        )
        get_logger().log_info(f"Unlock node {standby_hostname}")
        system_host_lock_unlock_keywords.unlock_host(standby_hostname)

        get_logger().log_info("Swact controllers")
        SystemHostSwactKeywords(ssh_connection).host_swact()

        get_logger().log_test_case_step(f"Upgrade kubelet on controller {active_hostname} (batch {batch_num}/{len(batches)})")
        get_logger().log_info(f"Locking node {active_hostname}")
        system_host_lock_unlock_keywords.lock_host(active_hostname)
        kube_host_upgrade_keywords.kube_host_upgrade_kubelet(active_hostname)
        kube_host_upgrade_list_keywords.wait_for_host_upgrade_status(
            active_hostname,
            "upgraded-kubelet",
            timeout=600,
            failure_statuses=["upgrading-kubelets-failed"],
        )
        get_logger().log_info(f"Unlock node {active_hostname}")
        system_host_lock_unlock_keywords.unlock_host(active_hostname)

    # check if lab has compute nodes to upgrade kubelet
    hosts = system_host_list_keywords.get_system_host_list().get_hosts()
    if len(hosts) > 2:
        get_logger().log_test_case_step("Upgrade kubelet on worker nodes")
        workers = system_host_list_keywords.get_system_host_list().get_computer_names()
        for worker in workers:
            get_logger().log_info(f"Locking worker node {worker}")
            system_host_lock_unlock_keywords.lock_host(worker)
            kube_host_upgrade_keywords.kube_host_upgrade_kubelet(worker)
            kube_host_upgrade_list_keywords.wait_for_host_upgrade_status(
                worker,
                "upgraded-kubelet",
                timeout=600,
                failure_statuses=["upgrading-kubelets-failed"],
            )
            get_logger().log_info(f"Unlock worker node {worker}")
            system_host_lock_unlock_keywords.unlock_host(worker)

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

    get_logger().log_test_case_step("Verify host upgraded via kube-host-upgrade-list")
    host_upgrade_list = kube_host_upgrade_list_keywords.kube_host_upgrade_list()
    controllers = system_host_list_keywords.get_system_host_list().get_controller_names()
    for controller in controllers:
        host_upgrade = host_upgrade_list.get_host_upgrade_by_hostname(controller)
        validate_equals(host_upgrade.get_control_plane_version(), target_version, f"{controller} control-plane upgraded")
        validate_equals(host_upgrade.get_kubelet_version(), target_version, f"{controller} kubelet upgraded")
    if len(hosts) > 2:
        workers = system_host_list_keywords.get_system_host_list().get_computer_names()
        for worker in workers:
            host_upgrade = host_upgrade_list.get_host_upgrade_by_hostname(worker)
            validate_equals(host_upgrade.get_kubelet_version(), target_version, f"{worker} kubelet upgraded")
