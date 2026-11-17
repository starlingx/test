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

# Feature labels that are not a stable property of the node and therefore must
# not be required to come back after a reboot. On StarlingX the ceph-common
# rbdmap service loads the kernel 'nbd' module during boot, which registers 16
# empty nbd block devices reporting rotational=0. NFD's storage source turns
# that into feature.node.kubernetes.io/storage-nonrotationaldisk even though the
# real disks are rotational and no nbd device is in use. Because the nbd module
# loads late and non-deterministically at boot (and the backing rbdmap service
# does not run RBD maps here -- ceph-csi uses krbd), this label appears and
# disappears on a timing that does not reflect any real hardware feature.
VOLATILE_FEATURE_NODE_LABELS = {
    "feature.node.kubernetes.io/storage-nonrotationaldisk",
}


def get_feature_node_labels(ssh_connection, host_name: str) -> list:
    """Gets the list of feature.node label keys for a specific node."""
    labels_output = KubectlNodesKeywords(ssh_connection).get_node_labels(host_name)
    return labels_output.get_keys_by_prefix(FEATURE_NODE_LABEL_PREFIX)


def feature_node_labels_restored(ssh_connection, host_name: str, expected_label_keys: set) -> bool:
    """Checks that the node again carries every stable feature.node label it had.

    The restored set is compared by key rather than by count. Different nodes can
    expose a different number of feature labels (hardware/BIOS driven), and on a
    duplex system a forced reboot swacts the active controller, so an exact-count
    comparison against a single captured number is unreliable. Requiring the
    original keys to be a subset of the current ones verifies the intent -- that
    the labels the node previously advertised were re-published -- without
    depending on the absolute count or on which controller is currently active.

    Labels listed in VOLATILE_FEATURE_NODE_LABELS are ignored on both sides: they
    do not reflect a stable node feature (see that set's documentation) and would
    make the check flaky.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        host_name (str): the node whose labels are inspected.
        expected_label_keys (set): the feature.node label keys captured originally.

    Returns:
        bool: True when every originally present stable label key is present again.
    """
    expected_stable = set(expected_label_keys) - VOLATILE_FEATURE_NODE_LABELS
    current = set(get_feature_node_labels(ssh_connection, host_name)) - VOLATILE_FEATURE_NODE_LABELS
    return expected_stable.issubset(current)


def install_nfd(ssh_connection: SSHConnection) -> None:
    """Uploads and applies NFD if not already applied.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """
    app_config = ConfigurationManager.get_app_config()
    nfd_name = app_config.get_node_feature_discovery_app_name()
    # When this runs right after another test rebooted a controller (swact), the
    # sysinv application API briefly rejects operations with "Kubernetes
    # endpoints are not accessible for application operations". Wait for the API
    # to come back before upload/apply so the install does not fail on a
    # transient post-reboot condition.
    KubectlGetPodsKeywords(ssh_connection).wait_for_kubernetes_api_available(timeout=600)
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
    host_name = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()  # before the finalizer

    get_logger().log_test_case_step("Ensuring NFD application is installed and applied")
    install_nfd(ssh_connection)

    get_logger().log_test_case_step("Counting feature.node labels before deletion")
    validate_equals_with_retry(
        lambda: len(get_feature_node_labels(LabConnectionKeywords().get_active_controller_ssh(), host_name)) > 0,
        True,
        "Feature node labels should be present",
        timeout=360,
        polling_sleep_time=60,
    )
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    feature_labels = get_feature_node_labels(ssh_connection, host_name)
    label_count_before = len(feature_labels)
    expected_label_keys = set(feature_labels)
    get_logger().log_info(f"Feature node label count: {label_count_before}")

    pre_uptime = SystemHostListKeywords(ssh_connection).get_uptime(host_name)  # before the finalizer

    def cleanup_nfd_reboot_test():
        get_logger().log_teardown_step(f"Removing {nfd_name} app")
        cleanup_ssh = LabConnectionKeywords().get_active_controller_ssh()  # fresh and independent connection
        SystemHostRebootKeywords(cleanup_ssh).wait_for_force_reboot(host_name, pre_uptime)  # wait for host to be back online before cleanup
        # Wait until the rebooted host is fully 'available' again. Being back online
        # is not enough: right after a controller reboot/swact the Kubernetes
        # endpoints are briefly unavailable and 'system application-remove' is
        # rejected ("Kubernetes endpoints are not accessible for application
        # operations"). Waiting for availability lets the cluster recover first.
        SystemHostListKeywords(LabConnectionKeywords().get_active_controller_ssh()).wait_for_host_availability(host_name, ["available"])
        install_nfd(LabConnectionKeywords().get_active_controller_ssh())  # ensure NFD is applied to restore labels
        validate_equals_with_retry(
            lambda: feature_node_labels_restored(LabConnectionKeywords().get_active_controller_ssh(), host_name, expected_label_keys),
            True,
            "Labels should be restored before removing NFD",
            timeout=360,
            polling_sleep_time=60,
        )
        SystemApplicationRemoveKeywords(LabConnectionKeywords().get_active_controller_ssh()).system_application_remove_and_delete_app(nfd_name)

    request.addfinalizer(cleanup_nfd_reboot_test)  # after label_count_before and pre_uptime are defined

    get_logger().log_test_case_step(f"Deleting all feature.node.kubernetes.io labels from {host_name}")
    label_keywords = KubectlLabelNodeKeywords(ssh_connection)
    for label_key in feature_labels:
        label_keywords.remove_label(host_name, label_key)

    get_logger().log_test_case_step("Validating feature.node label count is 0 after deletion")
    label_count_after_delete = len(get_feature_node_labels(ssh_connection, host_name))
    validate_equals(label_count_after_delete, 0, "Feature node label count should be 0 after deletion")

    get_logger().log_test_case_step(f"Force rebooting {host_name}")
    SystemHostRebootKeywords(ssh_connection).host_force_reboot()

    get_logger().log_test_case_step(f"Waiting for {host_name} to come back online after reboot")
    wait_ssh = LabConnectionKeywords().get_active_controller_ssh()  # fresh connection after reboot
    if not SystemHostRebootKeywords(wait_ssh).wait_for_force_reboot(host_name, pre_uptime):
        raise Exception(f"Timeout waiting for {host_name} to come back online after reboot.")

    get_logger().log_test_case_step(f"Waiting for {host_name} to reach availability 'available' after reboot")
    SystemHostListKeywords(LabConnectionKeywords().get_active_controller_ssh()).wait_for_host_availability(host_name, ["available"])

    # After the reboot the NFD worker pod restarts and runs its startup feature
    # discovery, re-publishing the stable feature labels. Volatile labels such as
    # storage-nonrotationaldisk are ignored by feature_node_labels_restored (see
    # VOLATILE_FEATURE_NODE_LABELS), so this no longer has to wait for the late,
    # non-deterministic nbd module load.
    get_logger().log_test_case_step("Validating feature.node labels are restored after reboot")
    validate_equals_with_retry(
        lambda: feature_node_labels_restored(LabConnectionKeywords().get_active_controller_ssh(), host_name, expected_label_keys),
        True,
        "Feature node labels should be restored after reboot",
        timeout=360,
        polling_sleep_time=60,
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
    host_name = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()  # before the finalizer

    get_logger().log_test_case_step("Ensuring NFD application is installed and applied")
    install_nfd(ssh_connection)

    get_logger().log_test_case_step("Counting feature.node labels before deletion")
    validate_equals_with_retry(
        lambda: len(get_feature_node_labels(LabConnectionKeywords().get_active_controller_ssh(), host_name)) > 0,
        True,
        "Feature node labels should be present",
        timeout=360,
        polling_sleep_time=60,
    )
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    feature_labels = get_feature_node_labels(ssh_connection, host_name)
    label_count_before = len(feature_labels)
    expected_label_keys = set(feature_labels)
    get_logger().log_info(f"Feature node label count: {label_count_before}")

    def cleanup_nfd_deletion_test():
        get_logger().log_teardown_step(f"Removing {nfd_name} app")
        cleanup_ssh = LabConnectionKeywords().get_active_controller_ssh()  # fresh and independent connection
        install_nfd(cleanup_ssh)  # ensure NFD is applied to restore labels
        validate_equals_with_retry(
            lambda: feature_node_labels_restored(LabConnectionKeywords().get_active_controller_ssh(), host_name, expected_label_keys),
            True,
            "Labels should be restored before removing NFD",
            timeout=360,
            polling_sleep_time=60,
        )
        SystemApplicationRemoveKeywords(cleanup_ssh).system_application_remove_and_delete_app(nfd_name)

    request.addfinalizer(cleanup_nfd_deletion_test)  # after label_count_before is defined

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
        expected_status="Running", namespace=NFD_NAMESPACE, timeout=360
    )

    get_logger().log_test_case_step("Waiting for NFD to restore labels after worker restart")
    validate_equals_with_retry(
        lambda: feature_node_labels_restored(LabConnectionKeywords().get_active_controller_ssh(), host_name, expected_label_keys),
        True,
        "Feature node labels should be restored after NFD re-labeling",
        timeout=360,
        polling_sleep_time=60,
    )