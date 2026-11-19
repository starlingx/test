from typing import Dict, Optional, Set

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.k8s.node.kubectl_label_node_keywords import KubectlLabelNodeKeywords
from keywords.k8s.node.kubectl_nodes_keywords import KubectlNodesKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords

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


def get_feature_node_label_keys(ssh_connection: SSHConnection, node_name: Optional[str] = None) -> Dict[str, Set[str]]:
    """Gets the feature.node label keys of one node, or of every node.

    Lists the labels with a single ``kubectl label node --list`` call and filters
    them on the Output object.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        node_name (Optional[str]): the node to inspect. If None, every node is inspected.

    Returns:
        Dict[str, Set[str]]: feature.node label keys, by node name.
    """
    labels_output = KubectlLabelNodeKeywords(ssh_connection).get_node_labels_list(node_name)
    return {name: set(labels_output.get_label_keys_on_node_by_prefix(name, FEATURE_NODE_LABEL_PREFIX)) for name in labels_output.get_node_names()}


def feature_node_labels_restored(ssh_connection: SSHConnection, expected_label_keys: Dict[str, Set[str]]) -> bool:
    """Checks that each node again carries every stable feature.node label it had.

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
        expected_label_keys (Dict[str, Set[str]]): the feature.node label keys captured originally, by node name.

    Returns:
        bool: True when every originally present stable label key is present again on its node.
    """
    current_label_keys = get_feature_node_label_keys(ssh_connection)
    for node_name, node_label_keys in expected_label_keys.items():
        expected_stable = node_label_keys - VOLATILE_FEATURE_NODE_LABELS
        current_stable = current_label_keys.get(node_name, set()) - VOLATILE_FEATURE_NODE_LABELS
        if not expected_stable.issubset(current_stable):
            return False
    return True


def register_uninstall_nfd_finalizer(request: FixtureRequest) -> None:
    """Registers a finalizer that uninstalls NFD on a fresh, independent SSH connection.

    Args:
        request (FixtureRequest): the pytest request fixture of the calling test.
    """
    nfd_name = ConfigurationManager.get_app_config().get_node_feature_discovery_app_name()

    def teardown_uninstall_nfd():
        get_logger().log_teardown_step(f"Uninstalling {nfd_name} app")
        uninstall_nfd(LabConnectionKeywords().get_active_controller_ssh())

    request.addfinalizer(teardown_uninstall_nfd)


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
        upload_keywords.system_application_upload(upload_input, timeout=360)
    else:
        get_logger().log_info(f"{nfd_name} is already uploaded. Skipping upload.")

    apply_keywords.system_application_apply(nfd_name, timeout=360)


def uninstall_nfd(ssh_connection: SSHConnection) -> None:
    """Removes and deletes NFD if it is present on the host.

    Safely handles both the 'applied' (remove + delete) and 'uploaded'
    (delete only) states via cleanup_app_if_present.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """
    app_config = ConfigurationManager.get_app_config()
    nfd_name = app_config.get_node_feature_discovery_app_name()
    # Default remove timeout is only 60s, which is too short for NFD to tear down
    # its daemonset pods. Use a budget aligned with the rest of this suite.
    SystemApplicationRemoveKeywords(ssh_connection).cleanup_app_if_present(
        nfd_name,
        timeout_in_seconds=360,
        check_interval_in_seconds=60,
    )


@mark.p1
def test_nfd_install_and_uninstall(request):
    """Verify node-feature-discovery application install and uninstall.

    Install the node-feature-discovery application using separate upload and
    apply keywords, verifying the application status after each step, then
    uninstall it using separate remove and delete keywords, again verifying the
    status after each step.

    Setup:
        - Clean up any pre-existing NFD app on the lab

    Steps:
        1. Upload the NFD application and verify status is uploaded
        2. Apply the NFD application and verify status is applied
        3. Verify the NFD pods reach the Running status
        4. Verify feature.node labels are present across all nodes
        5. Log the total number of feature.node labels across all nodes
        6. Remove the NFD application and verify status is uploaded
        7. Delete the NFD application and verify the deletion message
        8. Verify the NFD pods are deleted
        9. Verify feature.node labels are cleared across all nodes

    Teardown:
        - Remove and delete the NFD application if still present
    """
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    nfd_name = app_config.get_node_feature_discovery_app_name()
    nfd_file_path = f"{base_path}{nfd_name}*.tgz"
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    register_uninstall_nfd_finalizer(request)

    get_logger().log_setup_step("Cleaning up any pre-existing NFD app on the lab")
    uninstall_nfd(ssh_connection)

    # Step 1: Upload the NFD application
    get_logger().log_test_case_step("Upload the NFD application and verify status is uploaded")
    upload_input = SystemApplicationUploadInput()
    upload_input.set_app_name(nfd_name)
    upload_input.set_tar_file_path(nfd_file_path)
    upload_output = SystemApplicationUploadKeywords(ssh_connection).system_application_upload(upload_input, timeout=360)
    upload_object = upload_output.get_system_application_object()
    validate_equals(upload_object.get_name(), nfd_name, f"{nfd_name} name validation after upload")
    validate_equals(upload_object.get_status(), SystemApplicationStatusEnum.UPLOADED.value, f"{nfd_name} status validation after upload")

    # Step 2: Apply the NFD application
    get_logger().log_test_case_step("Apply the NFD application and verify status is applied")
    apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(nfd_name, timeout=360)
    apply_object = apply_output.get_system_application_object()
    validate_equals(apply_object.get_name(), nfd_name, f"{nfd_name} name validation after apply")
    validate_equals(apply_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{nfd_name} status validation after apply")

    # Step 3: Verify the NFD pods are running
    get_logger().log_test_case_step("Verify the NFD pods reach the Running status")
    pod_status = KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace=NFD_NAMESPACE, timeout=360)
    validate_equals(pod_status, True, "NFD pods are running")

    # Step 4: Verify feature.node labels are present across all nodes
    get_logger().log_test_case_step("Verify feature.node labels are present across all nodes")
    validate_equals_with_retry(
        lambda: KubectlLabelNodeKeywords(LabConnectionKeywords().get_active_controller_ssh()).count_labels_all_nodes_by_prefix(FEATURE_NODE_LABEL_PREFIX) > 0,
        True,
        "Feature node labels should be present across all nodes",
        timeout=360,
        polling_sleep_time=60,
    )

    # Step 5: Log the total number of feature.node labels across all nodes
    get_logger().log_test_case_step("Logging the total number of feature.node labels across all nodes")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()  # fresh connection
    total_labels = KubectlLabelNodeKeywords(ssh_connection).count_labels_all_nodes_by_prefix(FEATURE_NODE_LABEL_PREFIX)
    get_logger().log_info(f"Total feature.node labels across all nodes: {total_labels}")

    # Step 6: Remove the NFD application
    get_logger().log_test_case_step("Remove the NFD application and verify status is uploaded")
    remove_input = SystemApplicationRemoveInput()
    remove_input.set_app_name(nfd_name)
    remove_input.set_force_removal(False)
    remove_input.set_timeout_in_seconds(360)
    remove_input.set_check_interval_in_seconds(60)
    remove_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(remove_input)
    remove_object = remove_output.get_system_application_object()
    validate_equals(remove_object.get_name(), nfd_name, f"{nfd_name} name validation after remove")
    validate_equals(remove_object.get_status(), SystemApplicationStatusEnum.UPLOADED.value, f"{nfd_name} status validation after remove")

    # Step 7: Delete the NFD application
    get_logger().log_test_case_step("Delete the NFD application and verify the deletion message")
    delete_input = SystemApplicationDeleteInput()
    delete_input.set_app_name(nfd_name)
    delete_input.set_force_deletion(False)
    delete_msg = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(delete_input)
    validate_equals(delete_msg.strip(), f"Application {nfd_name} deleted.", f"{nfd_name} deletion message validation")

    # Step 8: Verify the NFD pods are deleted
    get_logger().log_test_case_step("Verify the NFD pods are deleted")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_be_deleted(namespace=NFD_NAMESPACE)

    # Step 9: Verify feature.node labels are cleared across all nodes
    get_logger().log_test_case_step("Verify feature.node labels are cleared across all nodes after removal")
    validate_equals_with_retry(
        lambda: KubectlLabelNodeKeywords(LabConnectionKeywords().get_active_controller_ssh()).count_labels_all_nodes_by_prefix(FEATURE_NODE_LABEL_PREFIX),
        0,
        "Feature node label count should be 0 across all nodes after NFD removal",
        timeout=360,
        polling_sleep_time=60,
    )


@mark.p1
def test_nfd_labels_persist_after_reboot(request):
    """
    Verify that node feature discovery labels are restored after a forced reboot,
    exercising every node in the cluster, one at a time (serial).

    For each node, its feature.node labels are deleted and the node is force
    rebooted directly over SSH (reboot -f). When the node under test is the
    active controller, a swact is performed before the reboot so the control
    plane stays available. After the node is back enabled/unlocked/available
    and the NFD pods are Running again, the node's stable feature.node label keys
    are validated to be present again.

    Setup:
        - Clean up any pre-existing NFD app on the lab

    Steps:
        1. Install (upload + apply) NFD
        2. Verify the NFD pods are Running
        3. Identify every node in the cluster
        4. For each node:
            4.1 Swact away from the node if it is the active controller
            4.2 Verify the NFD pods are Running, then count the node's
                feature.node labels and validate count > 0
            4.3 Delete all feature.node labels from the node and validate count is 0
            4.4 Force reboot the node via direct SSH (reboot -f) and wait for it
                to be enabled/unlocked/available again
            4.5 Verify the NFD pods are Running again
            4.6 Validate the node's original stable feature.node label keys are restored

    Teardown:
        - Wait for any force-rebooted host to be back online and available
        - Uninstall (remove + delete) the NFD app
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    register_uninstall_nfd_finalizer(request)

    pending_reboots: Dict[str, int] = {}

    def teardown_wait_for_rebooted_hosts():
        for host_name, pre_uptime in pending_reboots.items():
            get_logger().log_teardown_step(f"Waiting for {host_name} to be back online and available before uninstalling NFD")
            teardown_ssh = LabConnectionKeywords().get_active_controller_ssh()  # fresh and independent connection
            SystemHostRebootKeywords(teardown_ssh).wait_for_force_reboot(host_name, pre_uptime)
            SystemHostListKeywords(LabConnectionKeywords().get_active_controller_ssh()).wait_for_host_availability(host_name, ["available"])

    request.addfinalizer(teardown_wait_for_rebooted_hosts)

    get_logger().log_setup_step("Cleaning up any pre-existing NFD app on the lab")
    uninstall_nfd(ssh_connection)

    get_logger().log_test_case_step("Installing NFD application")
    install_nfd(ssh_connection)

    get_logger().log_test_case_step("Verifying NFD pods are Running")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace=NFD_NAMESPACE, timeout=360)

    get_logger().log_test_case_step("Identifying all nodes in the cluster")
    node_names = [node.get_name() for node in KubectlNodesKeywords(ssh_connection).get_kubectl_nodes().get_nodes()]
    get_logger().log_info(f"Cluster nodes: {node_names}")

    has_multiple_controllers = len(SystemHostListKeywords(ssh_connection).get_controllers()) > 1
    get_logger().log_info(f"Cluster has multiple controllers: {has_multiple_controllers}")

    for node_name in node_names:
        # Swact only when the node to be rebooted is the active controller: the
        # active controller cannot be rebooted out from under the control plane.
        # This only applies to multi-controller systems; a simplex system has no
        # standby to swact to.
        if has_multiple_controllers and SystemHostListKeywords(ssh_connection).is_active_controller(node_name):
            get_logger().log_test_case_step(f"Swacting away from {node_name} because it is the active controller")
            SystemHostSwactKeywords(ssh_connection).host_swact()
            # After the swact the new active controller's kube-apiserver is briefly
            # unavailable (SSH drop, then "Forbidden" on kubectl until RBAC settles).
            # Wait for the Kubernetes API to be usable again before reading labels.
            ssh_connection = LabConnectionKeywords().get_active_controller_ssh()  # fresh connection after swact
            KubectlGetPodsKeywords(ssh_connection).wait_for_kubernetes_api_available(timeout=300)

        get_logger().log_test_case_step(f"Verifying NFD pods are Running before counting labels on {node_name}")
        KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace=NFD_NAMESPACE, timeout=360)

        get_logger().log_test_case_step(f"Counting feature.node labels on {node_name} before deletion")
        validate_equals_with_retry(
            lambda node_name=node_name: KubectlLabelNodeKeywords(LabConnectionKeywords().get_active_controller_ssh()).count_labels_on_node_by_prefix(node_name, FEATURE_NODE_LABEL_PREFIX) > 0,
            True,
            f"Feature node labels should be present on {node_name}",
            timeout=360,
            polling_sleep_time=60,
        )
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()  # fresh connection
        expected_label_keys = get_feature_node_label_keys(ssh_connection, node_name)
        get_logger().log_info(f"Feature node label count on {node_name}: {len(expected_label_keys[node_name])}")

        get_logger().log_test_case_step(f"Deleting all feature.node labels from {node_name} and validating count is 0 (with retry)")
        validate_equals_with_retry(
            lambda node_name=node_name: KubectlLabelNodeKeywords(LabConnectionKeywords().get_active_controller_ssh()).remove_labels_on_node_by_prefix(node_name, FEATURE_NODE_LABEL_PREFIX),
            0,
            f"Feature node label count should be 0 on {node_name} after deletion",
            timeout=360,
            polling_sleep_time=60,
        )

        get_logger().log_test_case_step(f"Force rebooting {node_name} via direct SSH")
        active_ssh = LabConnectionKeywords().get_active_controller_ssh()  # fresh connection
        pre_uptime = SystemHostListKeywords(active_ssh).get_uptime(node_name)
        pending_reboots[node_name] = pre_uptime
        node_ssh = LabConnectionKeywords().get_ssh_for_hostname(node_name)
        SystemHostRebootKeywords(node_ssh).host_force_reboot_no_wait()

        get_logger().log_test_case_step(f"Waiting for {node_name} to come back online after reboot")
        wait_ssh = LabConnectionKeywords().get_active_controller_ssh()  # fresh connection after reboot
        if not SystemHostRebootKeywords(wait_ssh).wait_for_force_reboot(node_name, pre_uptime):
            raise Exception(f"Timeout waiting for {node_name} to come back online after reboot.")

        get_logger().log_test_case_step(f"Waiting for {node_name} to reach availability 'available' after reboot")
        SystemHostListKeywords(LabConnectionKeywords().get_active_controller_ssh()).wait_for_host_availability(node_name, ["available"])
        del pending_reboots[node_name]

        get_logger().log_test_case_step("Verifying NFD pods are Running again")
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()  # fresh connection after reboot
        KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace=NFD_NAMESPACE, timeout=360)

        get_logger().log_test_case_step(f"Validating feature.node labels on {node_name} are restored after reboot")
        validate_equals_with_retry(
            lambda expected_label_keys=expected_label_keys: feature_node_labels_restored(LabConnectionKeywords().get_active_controller_ssh(), expected_label_keys),
            True,
            f"Feature node labels on {node_name} should be restored after reboot",
            timeout=360,
            polling_sleep_time=60,
        )


@mark.p1
def test_nfd_labels_restored_after_deletion(request):
    """
    Verify that node feature discovery labels are restored after deletion
    by restarting the NFD pods to force a full re-scan.

    The labels are counted, deleted and validated across every node in the
    cluster, not just the active controller.

    Setup:
        - Clean up any pre-existing NFD app on the lab

    Steps:
        1. Install (upload + apply) NFD
        2. Verify the NFD pods are Running
        3. Capture the feature.node label keys of all nodes and validate count > 0
        4. Delete all feature.node labels from every node and validate the total count is 0
        5. Delete the NFD pods
        6. Verify the NFD pods are Running again
        7. Validate the original stable feature.node label keys are restored on every node

    Teardown:
        - Uninstall (remove + delete) the NFD app
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    register_uninstall_nfd_finalizer(request)

    get_logger().log_setup_step("Cleaning up any pre-existing NFD app on the lab")
    uninstall_nfd(ssh_connection)

    get_logger().log_test_case_step("Installing NFD application")
    install_nfd(ssh_connection)

    get_logger().log_test_case_step("Verifying NFD pods are Running")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace=NFD_NAMESPACE, timeout=360)

    get_logger().log_test_case_step("Counting feature.node labels across all nodes before deletion")
    validate_equals_with_retry(
        lambda: KubectlLabelNodeKeywords(LabConnectionKeywords().get_active_controller_ssh()).count_labels_all_nodes_by_prefix(FEATURE_NODE_LABEL_PREFIX) > 0,
        True,
        "Feature node labels should be present on the cluster",
        timeout=360,
        polling_sleep_time=60,
    )
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    expected_label_keys = get_feature_node_label_keys(ssh_connection)
    get_logger().log_info(f"Total feature.node label count across all nodes: {sum(len(keys) for keys in expected_label_keys.values())}")

    get_logger().log_test_case_step("Deleting all feature.node labels from every node and validating count is 0 (with retry)")
    validate_equals_with_retry(
        lambda: KubectlLabelNodeKeywords(LabConnectionKeywords().get_active_controller_ssh()).remove_labels_all_nodes_by_prefix(FEATURE_NODE_LABEL_PREFIX),
        0,
        "Feature node label count should be 0 across all nodes after deletion",
        timeout=360,
        polling_sleep_time=60,
    )

    get_logger().log_test_case_step("Deleting all NFD pods to force re-labeling")
    KubectlDeletePodsKeywords(ssh_connection).delete_all_pods(namespace=NFD_NAMESPACE)

    get_logger().log_test_case_step("Verifying NFD pods are Running again")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace=NFD_NAMESPACE, timeout=360)

    get_logger().log_test_case_step("Waiting for NFD to restore labels across all nodes after pod restart")
    validate_equals_with_retry(
        lambda: feature_node_labels_restored(LabConnectionKeywords().get_active_controller_ssh(), expected_label_keys),
        True,
        "Feature node labels should be restored on every node after NFD re-labeling",
        timeout=360,
        polling_sleep_time=60,
    )
