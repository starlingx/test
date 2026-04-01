"""
Test Kubernetes Node Failure KPIs

This test measures two KPIs in sequence:
1. Node Failure Detection Time - Time for Kubernetes to detect node failure
2. Workload Rescheduling Time - Time for workloads to be rescheduled after detection
"""
import json
import time
from datetime import datetime

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_greater_than_or_equal, validate_not_none, validate_equals_with_retry
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.k8s.node.kubectl_nodes_keywords import KubectlNodesKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.kpi.node_failure_kpi_keywords import cleanup_test_resources
from keywords.kpi.node_failure_kpi_keywords import create_html_report
from keywords.kpi.node_failure_kpi_keywords import create_test_deployment
from keywords.kpi.node_failure_kpi_keywords import label_node
from keywords.kpi.node_failure_kpi_keywords import read_existing_iterations
from keywords.kpi.node_failure_kpi_keywords import setup_namespace_and_image
from keywords.kpi.node_failure_kpi_keywords import wait_for_node_status
from keywords.kpi.node_failure_kpi_keywords import wait_for_pods_rescheduled



@mark.p1
@mark.lab_has_worker
@mark.lab_has_processor_min_2
def test_kubernetes_node_failure_kpis_workers(request):
    """
    Test Kubernetes Node Failure KPIs on Worker Nodes (Detection + Rescheduling)

    Requirements:
    - At least 2 dedicated compute/worker nodes (not AIO controllers)

    Test Steps:
    - Verify system has at least 2 dedicated compute nodes
    - Execute node failure KPI test flow using compute nodes

    Cleanup:
      - Delete the test deployment
      - Remove node labels
      - Wait for node to come back online

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    
    get_logger().log_test_case_step("Verify system has at least 2 dedicated compute nodes")
    computes = SystemHostListKeywords(ssh_connection).get_computes()
    validate_greater_than_or_equal(len(computes), 2, f"At least 2 dedicated compute nodes are required, found {len(computes)}")
    
    target_node = computes[0].get_host_name()
    backup_node = computes[1].get_host_name()
    get_logger().log_info(f"Selected compute nodes: target={target_node}, backup={backup_node}")
    
    execute_node_failure_kpi_test(request, ssh_connection, target_node, backup_node, node_type="worker")


@mark.p1
@mark.lab_is_duplex
def test_kubernetes_node_failure_kpis_aio_controllers(request):
    """
    Test Kubernetes Node Failure KPIs on AIO-DX Controllers (Detection + Rescheduling)

    Requirements:
    - AIO-DX system (2 controllers with worker capability)

    Test Steps:
    - Verify system is AIO-DX with 2 controllers
    - Execute node failure KPI test flow using controller nodes

    Cleanup:
      - Delete the test deployment
      - Remove node labels
      - Wait for node to come back online

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    
    get_logger().log_test_case_step("Verify system is AIO-DX with 2 controllers")
    system_host_keywords = SystemHostListKeywords(ssh_connection)
    controllers = system_host_keywords.get_controllers()
    validate_equals(len(controllers), 2, f"Test requires AIO-DX system with 2 controllers, found {len(controllers)}")
    
    standby_controller = system_host_keywords.get_standby_controller()
    validate_not_none(standby_controller, "No standby controller found in AIO-DX system")
    
    active_controller = system_host_keywords.get_active_controller()
    validate_not_none(active_controller, "No active controller found in AIO-DX system")
    
    target_node = standby_controller.get_host_name()
    backup_node = active_controller.get_host_name()
    get_logger().log_info(f"Selected AIO-DX controllers: target={target_node} (standby), backup={backup_node} (active)")
    
    execute_node_failure_kpi_test(request, ssh_connection, target_node, backup_node, node_type="controller")


def execute_node_failure_kpi_test(request, ssh_connection: SSHConnection, target_node: str, backup_node: str, node_type: str):
    """
    Executes the node failure KPI test flow

    Args:
        request: pytest request fixture for finalizers
        ssh_connection (SSHConnection): SSH connection to active controller
        target_node (str): name of the node to reboot (where pods will be placed)
        backup_node (str): name of the backup node (where pods will reschedule)
        node_type (str): type of nodes being tested ("worker" or "controller")

    """
    namespace = "kpi-node-failure"
    target_pods = 30
    
    get_logger().log_info(f"Starting node failure KPI test on {node_type} nodes: target={target_node}, backup={backup_node}")
    
    get_logger().log_test_case_step(f"Label target {node_type} node for pod placement")
    label_node(ssh_connection, target_node)

    get_logger().log_test_case_step("Create namespace and prepare busybox image")
    setup_namespace_and_image(ssh_connection, namespace)
    local_registry = ConfigurationManager.get_docker_config().get_local_registry().get_registry_url()

    def cleanup_deployment():
        """Finalizer to cleanup deployment and wait for node"""
        cleanup_test_resources(ssh_connection, namespace, target_node, backup_node)

    request.addfinalizer(cleanup_deployment)
    
    get_logger().log_test_case_step(f"Create deployment with {target_pods} replicas on {target_node} ({node_type})")
    pod_getter = create_test_deployment(ssh_connection, namespace, target_pods, local_registry, target_node)
    
    get_logger().log_test_case_step("Verify all pods are on target node")
    
    def get_pods_on_target_node():
        """Helper function to get count of pods on target node"""
        kpi_pods = [p for p in pod_getter.get_pods(namespace).get_pods() if p.get_name().startswith("kpi-test-deployment")]
        pods_on_target = [p for p in kpi_pods if p.get_node() == target_node]
        get_logger().log_info(f"Found {len(pods_on_target)} pods running on {target_node}")
        return len(pods_on_target)
    
    validate_equals_with_retry(
        get_pods_on_target_node,
        target_pods,
        f"Expected {target_pods} pods on {target_node}",
        timeout=300,
        polling_sleep_time=10
    )
    
    get_logger().log_test_case_step("Capture initial pod UIDs for tracking")
    
    def get_pod_uids():
        """Helper function to get pod UIDs"""
        output = ssh_connection.send(f"export KUBECONFIG=/etc/kubernetes/admin.conf; kubectl get pods -n {namespace} -l app=kpi-test -o json")
        validate_equals(ssh_connection.get_return_code(), 0, "Successfully retrieved pod UIDs")
        return json.loads("".join(output))
    
    initial_pods_json = get_pod_uids()
    initial_pod_uids = [pod["metadata"]["uid"] for pod in initial_pods_json.get("items", [])]
    validate_equals(len(initial_pod_uids), target_pods, f"Expected {target_pods} pod UIDs, found {len(initial_pod_uids)}")
    get_logger().log_info(f"Captured {len(initial_pod_uids)} initial pod UIDs")
    
    get_logger().log_test_case_step(f"Verify target {node_type} node is currently Ready")
    nodes = KubectlNodesKeywords(ssh_connection).get_kubectl_nodes()
    node = nodes.get_node(target_node)
    validate_not_none(node, f"Node {target_node} not found")
    validate_equals(node.get_status(), "Ready", f"Node {target_node} is not Ready")
    
    get_logger().log_test_case_step(f"Verify backup {node_type} node is Ready")
    backup_node_obj = nodes.get_node(backup_node)
    validate_not_none(backup_node_obj, f"Backup node {backup_node} not found")
    validate_equals(backup_node_obj.get_status(), "Ready", f"Backup node {backup_node} is not Ready")
    
    get_logger().log_test_case_step(f"Label backup {node_type} node to allow pod rescheduling")
    label_node(ssh_connection, backup_node)
    get_logger().log_info(f"Backup node {backup_node} labeled for pod rescheduling")
    
    get_logger().log_test_case_step(f"Record failure start time and reboot the {node_type} node")
    failure_start_time = time.time()
    failure_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    get_logger().log_info(f"Failure start time: {failure_time_str}")
    
    if node_type == "controller":
        get_logger().log_info(f"Getting SSH connection to standby controller {target_node}")
        node_ssh = LabConnectionKeywords().get_standby_controller_ssh()
        get_logger().log_info(f"Sending reboot command to {target_node}")
        node_ssh.send_as_sudo("reboot")
        get_logger().log_info(f"Reboot command return code: {node_ssh.get_return_code()}")
    else:
        get_logger().log_info(f"Getting SSH connection to worker {target_node}")
        node_ssh = LabConnectionKeywords().get_ssh_for_hostname(target_node)
        get_logger().log_info(f"Sending reboot command to {target_node}")
        node_ssh.send_as_sudo("reboot")
        get_logger().log_info(f"Reboot command return code: {node_ssh.get_return_code()}")
    
    get_logger().log_info(f"Reboot command sent to {target_node}, waiting for node to go NotReady...")
    
    get_logger().log_test_case_step("KPI #1: Monitor node status until NotReady is detected")
    get_logger().log_info(f"Monitoring node '{target_node}' for NotReady status")

    detection_time, detection_time_str = wait_for_node_status(ssh_connection, target_node, "NotReady", 300)
    
    validate_not_none(detection_time, "Node was not detected as NotReady within timeout")
    detection_duration = detection_time - failure_start_time
    get_logger().log_info(f"KPI #1 - Node failure detection time: {detection_duration:.2f} seconds")
    
    get_logger().log_test_case_step("KPI #2: Monitor pods until rescheduled (by creation time)")
    recovery_time, recovery_time_str, rescheduled_count = wait_for_pods_rescheduled(ssh_connection, namespace, target_node, target_pods, initial_pod_uids, 600)
    
    rescheduling_duration = recovery_time - detection_time
    get_logger().log_info(f"KPI #2 - Workload rescheduling time: {rescheduling_duration:.2f} seconds")
    
    get_logger().log_test_case_step(f"Wait for {target_node} to be unlocked, enabled, and available")
    get_logger().log_info(f"Waiting for {target_node} to complete reboot and return to service...")
    is_unlocked = SystemHostLockKeywords(ssh_connection).wait_for_host_unlocked(target_node, unlock_wait_timeout=2800)
    if is_unlocked:
        get_logger().log_info(f"{target_node} is now unlocked, enabled, and available")
    else:
        get_logger().log_info(f"WARNING: {target_node} did not return to unlocked/enabled/available state within timeout")
    
    get_logger().log_test_case_step("Update KPI report with both measurements")
    existing_iterations = read_existing_iterations(node_type)
    
    new_iteration = {
        "node_name": target_node,
        "failure_time": failure_time_str,
        "detection_time_str": detection_time_str,
        "detection_time": detection_duration,
        "pods_count": target_pods,
        "recovery_time_str": recovery_time_str,
        "rescheduling_time": rescheduling_duration
    }
    
    existing_iterations.append(new_iteration)
    create_html_report(existing_iterations, node_type)
    
    get_logger().log_info(f"KPI measurements completed - Detection: {detection_duration:.2f}s, Rescheduling: {rescheduling_duration:.2f}s")
