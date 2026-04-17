from pytest import mark

from config.configuration_manager import ConfigurationManager
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords, SystemApplicationUploadInput
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.k8s.node.kubectl_label_node_keywords import KubectlLabelNodeKeywords
from keywords.k8s.node.kubectl_nodes_keywords import KubectlNodesKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry

NFD_NAMESPACE = "node-feature-discovery"


FEATURE_NODE_LABEL_PREFIX = "feature.node"


def get_feature_node_labels(ssh_connection, host_name: str) -> list:
    """Gets the list of feature.node label keys for a specific node."""
    labels_output = KubectlNodesKeywords(ssh_connection).get_node_labels(host_name)
    return labels_output.get_keys_by_prefix(FEATURE_NODE_LABEL_PREFIX)


def install_nfd(ssh_connection: SSHConnection) -> None:
    """Uploads and applies NFD if not already applied.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """
    app_config = ConfigurationManager.get_app_config()
    nfd_name = app_config.get_node_feature_discovery_app_name()
    apply_keywords = SystemApplicationApplyKeywords(ssh_connection)
    if apply_keywords.is_already_applied(nfd_name):
        get_logger().log_info(f"{nfd_name} is already applied.")
        return

    upload_keywords = SystemApplicationUploadKeywords(ssh_connection)
    if not upload_keywords.is_already_uploaded(nfd_name):
        base_path = app_config.get_base_application_path()
        upload_input = SystemApplicationUploadInput()
        upload_input.set_app_name(nfd_name)
        upload_input.set_tar_file_path(f"{base_path}{nfd_name}*.tgz")
        upload_keywords.system_application_upload(upload_input)
    else:
        get_logger().log_info(f"{nfd_name} is already uploaded. Skipping upload.")

    apply_keywords.system_application_apply(nfd_name)


@mark.p1
def test_nfd_labels_persist_after_reboot(request):
    """
    Verify that node feature discovery labels are restored after a forced reboot.

    Steps:
        1. Ensure NFD is installed
        2. Count feature.node labels and validate count > 0
        3. Delete all feature.node.kubernetes.io labels from controller-0
        4. Validate label count is 0
        5. Force reboot the host
        6. Wait for host to come back online
        7. Validate label count matches the original count
    """
    app_config = ConfigurationManager.get_app_config()
    nfd_name = app_config.get_node_feature_discovery_app_name()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    def cleanup_nfd_reboot_test():
        get_logger().log_teardown_step(f"Removing {nfd_name} app")
        SystemApplicationRemoveKeywords(ssh_connection).system_application_remove_and_delete_app(nfd_name)

    request.addfinalizer(cleanup_nfd_reboot_test)

    host_name = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_test_case_step("Ensuring NFD application is installed and applied")
    install_nfd(ssh_connection)

    get_logger().log_test_case_step("Counting feature.node labels before deletion")
    validate_equals_with_retry(
        lambda: len(get_feature_node_labels(LabConnectionKeywords().get_active_controller_ssh(), host_name)) > 0,
        True,
        "Feature node labels should be present",
        timeout=300,
        polling_sleep_time=30,
    )
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    feature_labels = get_feature_node_labels(ssh_connection, host_name)
    label_count_before = len(feature_labels)
    get_logger().log_info(f"Feature node label count: {label_count_before}")

    get_logger().log_test_case_step(f"Deleting all feature.node.kubernetes.io labels from {host_name}")
    label_keywords = KubectlLabelNodeKeywords(ssh_connection)
    for label_key in feature_labels:
        label_keywords.remove_label(host_name, label_key)

    get_logger().log_test_case_step("Validating feature.node label count is 0 after deletion")
    label_count_after_delete = len(get_feature_node_labels(ssh_connection, host_name))
    validate_equals(label_count_after_delete, 0, "Feature node label count should be 0 after deletion")

    get_logger().log_test_case_step(f"Force rebooting {host_name}")
    pre_uptime = SystemHostListKeywords(ssh_connection).get_uptime(host_name)
    reboot_kw = SystemHostRebootKeywords(ssh_connection)
    reboot_kw.host_force_reboot()

    get_logger().log_test_case_step(f"Waiting for {host_name} to come back online after reboot")
    if not reboot_kw.wait_for_force_reboot(host_name, pre_uptime):
        raise Exception(f"Timeout waiting for {host_name} to come back online after reboot.")

    get_logger().log_test_case_step("Validating feature.node labels are restored after reboot")
    validate_equals_with_retry(
        lambda: len(get_feature_node_labels(LabConnectionKeywords().get_active_controller_ssh(), host_name)),
        label_count_before,
        "Feature node label count should match original count after reboot",
        timeout=300,
        polling_sleep_time=30,
    )


@mark.p1
def test_nfd_labels_restored_after_deletion(request):
    """
    Verify that node feature discovery labels are restored after deletion
    by restarting the NFD worker pods to force a full re-scan.

    Steps:
        1. Ensure NFD is installed and applied
        2. Count feature.node labels and validate count > 0
        3. Delete all feature.node.kubernetes.io labels
        4. Validate label count is 0
        5. Restart NFD worker pods to trigger re-labeling
        6. Wait for labels to be restored by NFD
    """
    app_config = ConfigurationManager.get_app_config()
    nfd_name = app_config.get_node_feature_discovery_app_name()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    def cleanup_nfd_deletion_test():
        get_logger().log_teardown_step(f"Removing {nfd_name} app")
        SystemApplicationRemoveKeywords(ssh_connection).system_application_remove_and_delete_app(nfd_name)

    request.addfinalizer(cleanup_nfd_deletion_test)

    host_name = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_test_case_step("Ensuring NFD application is installed and applied")
    install_nfd(ssh_connection)

    get_logger().log_test_case_step("Counting feature.node labels before deletion")
    validate_equals_with_retry(
        lambda: len(get_feature_node_labels(LabConnectionKeywords().get_active_controller_ssh(), host_name)) > 0,
        True,
        "Feature node labels should be present",
        timeout=300,
        polling_sleep_time=30,
    )
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    feature_labels = get_feature_node_labels(ssh_connection, host_name)
    label_count_before = len(feature_labels)
    get_logger().log_info(f"Feature node label count: {label_count_before}")

    get_logger().log_test_case_step(f"Deleting all feature.node.kubernetes.io labels from {host_name}")
    label_keywords = KubectlLabelNodeKeywords(ssh_connection)
    for label_key in feature_labels:
        label_keywords.remove_label(host_name, label_key)

    get_logger().log_test_case_step("Validating feature.node label count is 0 after deletion")
    label_count_after_delete = len(get_feature_node_labels(ssh_connection, host_name))
    validate_equals(label_count_after_delete, 0, "Feature node label count should be 0 after deletion")

    get_logger().log_test_case_step("Restarting NFD worker pods to force re-labeling")
    pods_kw = KubectlGetPodsKeywords(ssh_connection)
    delete_kw = KubectlDeletePodsKeywords(ssh_connection)
    nfd_worker_pods = pods_kw.get_pods(namespace=NFD_NAMESPACE, label="role=worker").get_pods()
    for pod in nfd_worker_pods:
        get_logger().log_info(f"Deleting pod {pod.get_name()}")
        delete_kw.delete_pod(pod.get_name(), NFD_NAMESPACE)

    get_logger().log_test_case_step("Waiting for NFD worker pods to be Running")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(
        expected_status="Running", namespace=NFD_NAMESPACE, timeout=300
    )

    get_logger().log_test_case_step("Waiting for NFD to restore labels after worker restart")
    validate_equals_with_retry(
        lambda: len(get_feature_node_labels(LabConnectionKeywords().get_active_controller_ssh(), host_name)),
        label_count_before,
        "Feature node label count should match original count after NFD re-labeling",
        timeout=300,
        polling_sleep_time=60,
    )
