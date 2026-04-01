"""
Keywords for Kubernetes Node Failure KPI Testing

This module provides helper functions for measuring node failure detection
and workload rescheduling KPIs in Kubernetes environments.
"""
import json
import os
import re
import time
from datetime import datetime
from typing import List

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from keywords.docker.images.docker_images_keywords import DockerImagesKeywords
from keywords.docker.images.docker_load_image_keywords import DockerLoadImageKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.node.kubectl_nodes_keywords import KubectlNodesKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords


def get_kpi_report_path(node_type: str) -> str:
    """
    Gets the path for the KPI report HTML file

    Args:
        node_type (str): type of nodes being tested ("worker" or "controller")

    Returns:
        str: path to the KPI report file

    """
    return get_stx_resource_path(f"testcases/cloud_platform/kpi/node_failure_kpis_{node_type}.html")


def create_html_report(iterations: List[dict], node_type: str):
    """
    Creates or updates the HTML report with both KPI measurements

    Args:
        iterations (List[dict]): list of iteration results with both KPI measurements
        node_type (str): type of nodes being tested ("worker" or "controller")

    """
    if not iterations:
        return

    detection_times = [it["detection_time"] for it in iterations]
    rescheduling_times = [it["rescheduling_time"] for it in iterations]

    det_min = min(detection_times)
    det_max = max(detection_times)
    det_avg = sum(detection_times) / len(detection_times)

    resc_min = min(rescheduling_times)
    resc_max = max(rescheduling_times)
    resc_avg = sum(rescheduling_times) / len(rescheduling_times)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Kubernetes Node Failure KPIs Report - {node_type.capitalize()} Nodes</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
        }}
        h1 {{
            color: #1976D2;
        }}
        h2 {{
            color: #424242;
            margin-top: 30px;
        }}
        .kpi-description {{
            background-color: #E3F2FD;
            padding: 15px;
            border-left: 4px solid #1976D2;
            margin: 20px 0;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            max-width: 1200px;
            margin-top: 20px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #1976D2;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        tr:hover {{
            background-color: #ddd;
        }}
        .stats-row {{
            font-weight: bold;
            background-color: #E3F2FD;
        }}
        .timestamp {{
            font-size: 0.9em;
            color: #666;
        }}
        .highlight {{
            background-color: #FFF9C4 !important;
        }}
    </style>
</head>
<body>
    <h1>Kubernetes Node Failure KPIs Report - {node_type.capitalize()} Nodes</h1>
    <p><strong>Test Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p><strong>Node Type:</strong> {node_type.capitalize()}</p>
    <p><strong>Total Iterations:</strong> {len(iterations)}</p>

    <div class="kpi-description">
        <h3>KPI #1: Node Failure Detection Time</h3>
        <p><strong>Description:</strong> Time taken for Kubernetes to detect that a node has become unresponsive.</p>
        <p><strong>Measurement:</strong> From node reboot command until node status changes to NotReady.</p>
    </div>

    <h2>KPI #1: Node Failure Detection Results</h2>
    <table>
        <thead>
            <tr>
                <th>Iteration</th>
                <th>Node Name</th>
                <th>Failure Time</th>
                <th>Detection Time</th>
                <th>Duration (seconds)</th>
                <th>Note</th>
            </tr>
        </thead>
        <tbody>
"""

    for idx, iteration in enumerate(iterations, 1):
        highlight_class = "highlight" if iteration["detection_time"] == det_min else ""
        note = "Min" if iteration["detection_time"] == det_min else ("Max" if iteration["detection_time"] == det_max else "")
        html_content += f"""            <tr class="{highlight_class}">
                <td>{idx}</td>
                <td>{iteration['node_name']}</td>
                <td class="timestamp">{iteration['failure_time']}</td>
                <td class="timestamp">{iteration['detection_time_str']}</td>
                <td>{iteration['detection_time']:.2f}</td>
                <td>{note}</td>
            </tr>
"""

    html_content += f"""            <tr class="stats-row">
                <td colspan="4">Statistics</td>
                <td colspan="2">Min: {det_min:.2f}s | Max: {det_max:.2f}s | Avg: {det_avg:.2f}s</td>
            </tr>
        </tbody>
    </table>

    <div class="kpi-description">
        <h3>KPI #2: Workload Rescheduling Time</h3>
        <p><strong>Description:</strong> Recovery time of impacted workloads when a node failure is detected.</p>
        <p><strong>Measurement:</strong> From node NotReady detection until pods are created on other nodes (by creation timestamp, not Running status).</p>
        <p><strong>Note:</strong> Measures pod creation time to exclude image pull variance.</p>
    </div>

    <h2>KPI #2: Workload Rescheduling Results</h2>
    <table>
        <thead>
            <tr>
                <th>Iteration</th>
                <th>Node Name</th>
                <th>Pods Count</th>
                <th>Detection Time</th>
                <th>Recovery Time</th>
                <th>Duration (seconds)</th>
                <th>Note</th>
            </tr>
        </thead>
        <tbody>
"""

    for idx, iteration in enumerate(iterations, 1):
        highlight_class = "highlight" if iteration["rescheduling_time"] == resc_min else ""
        note = "Min" if iteration["rescheduling_time"] == resc_min else ("Max" if iteration["rescheduling_time"] == resc_max else "")
        html_content += f"""            <tr class="{highlight_class}">
                <td>{idx}</td>
                <td>{iteration['node_name']}</td>
                <td>{iteration['pods_count']}</td>
                <td class="timestamp">{iteration['detection_time_str']}</td>
                <td class="timestamp">{iteration['recovery_time_str']}</td>
                <td>{iteration['rescheduling_time']:.2f}</td>
                <td>{note}</td>
            </tr>
"""

    html_content += f"""            <tr class="stats-row">
                <td colspan="5">Statistics</td>
                <td colspan="2">Min: {resc_min:.2f}s | Max: {resc_max:.2f}s | Avg: {resc_avg:.2f}s</td>
            </tr>
        </tbody>
    </table>

    <p class="timestamp">Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</body>
</html>
"""

    report_path = get_kpi_report_path(node_type)
    with open(report_path, "w") as f:
        f.write(html_content)

    get_logger().log_info(f"KPI report updated: {report_path}")


def read_existing_iterations(node_type: str) -> List[dict]:
    """
    Reads existing iterations from the HTML report if it exists

    Args:
        node_type (str): type of nodes being tested ("worker" or "controller")

    Returns:
        List[dict]: list of existing iteration results

    """
    report_path = get_kpi_report_path(node_type)
    if not os.path.exists(report_path):
        return []

    iterations = []
    try:
        with open(report_path, "r") as f:
            content = f.read()

        pattern = r'<tr[^>]*>\s*<td>(\d+)</td>\s*<td>([^<]+)</td>\s*<td class="timestamp">([^<]+)</td>\s*<td class="timestamp">([^<]+)</td>\s*<td>([0-9.]+)</td>'
        detection_matches = re.findall(pattern, content)

        pattern2 = r'<tr[^>]*>\s*<td>(\d+)</td>\s*<td>([^<]+)</td>\s*<td>(\d+)</td>\s*<td class="timestamp">([^<]+)</td>\s*<td class="timestamp">([^<]+)</td>\s*<td>([0-9.]+)</td>'
        rescheduling_matches = re.findall(pattern2, content)

        for det_match, resc_match in zip(detection_matches, rescheduling_matches):
            iterations.append({
                "node_name": det_match[1],
                "failure_time": det_match[2],
                "detection_time_str": det_match[3],
                "detection_time": float(det_match[4]),
                "pods_count": int(resc_match[2]),
                "recovery_time_str": resc_match[4],
                "rescheduling_time": float(resc_match[5])
            })
    except Exception as e:
        get_logger().log_info(f"Could not read existing iterations: {e}")
        return []

    return iterations


def create_deployment_yaml(ssh_connection: SSHConnection, namespace: str, replicas: int, local_registry: str) -> str:
    """
    Creates a deployment YAML with nodeSelector to pin pods to labeled nodes

    Args:
        ssh_connection (SSHConnection): SSH connection to the controller
        namespace (str): namespace for the deployment
        replicas (int): number of pod replicas
        local_registry (str): local registry URL

    Returns:
        str: path to the created YAML file on remote system

    """
    yaml_content = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: kpi-test-deployment
  namespace: {namespace}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: kpi-test
  template:
    metadata:
      labels:
        app: kpi-test
    spec:
      nodeSelector:
        kpi-test-node: "true"
      imagePullSecrets:
      - name: kpi-registry-secret
      containers:
      - name: busybox
        image: {local_registry}/busybox:latest
        command: ["sh", "-c", "while true; do sleep 3600; done"]
        resources:
          requests:
            memory: "32Mi"
            cpu: "50m"
          limits:
            memory: "64Mi"
            cpu: "100m"
"""

    yaml_path = "/tmp/kpi_test_deployment.yaml"

    ssh_connection.send(f"cat > {yaml_path} << 'EOF'\n{yaml_content}\nEOF")
    assert ssh_connection.get_return_code() == 0, "Failed to create YAML file on remote system"

    return yaml_path


def prepare_busybox_image(ssh_connection: SSHConnection, namespace: str):
    """
    Pulls busybox image and pushes to local registry

    Args:
        ssh_connection (SSHConnection): SSH connection to the controller
        namespace (str): namespace where the secret will be created

    """
    local_registry = ConfigurationManager.get_docker_config().get_local_registry()

    get_logger().log_info(f"Creating secret for local registry in namespace {namespace}")
    KubectlCreateSecretsKeywords(ssh_connection).create_secret_for_registry(local_registry, "kpi-registry-secret", namespace)

    get_logger().log_info("Pulling busybox image from Docker Hub")
    DockerImagesKeywords(ssh_connection).pull_image("busybox:latest")
    assert ssh_connection.get_return_code() == 0, "Failed to pull busybox image"

    get_logger().log_info("Tagging and pushing busybox image to local registry")
    docker_load_keywords = DockerLoadImageKeywords(ssh_connection)
    docker_load_keywords.tag_docker_image_for_registry("busybox:latest", "busybox:latest", local_registry)
    docker_load_keywords.push_docker_image_to_registry("busybox:latest", local_registry)
    assert ssh_connection.get_return_code() == 0, "Failed to push busybox image to local registry"


def create_test_deployment(ssh_connection: SSHConnection, namespace: str, target_pods: int, local_registry: str, target_node: str) -> KubectlGetPodsKeywords:
    """
    Creates deployment with specified number of pods pinned to target node

    Args:
        ssh_connection (SSHConnection): SSH connection to the controller
        namespace (str): namespace for the deployment
        target_pods (int): number of pod replicas
        local_registry (str): local registry URL
        target_node (str): node name to pin pods to

    Returns:
        KubectlGetPodsKeywords: pod getter instance for monitoring

    """
    yaml_path = create_deployment_yaml(ssh_connection, namespace, target_pods, local_registry)
    ssh_connection.send(f"source /etc/platform/openrc; export KUBECONFIG=/etc/kubernetes/admin.conf; kubectl apply -f {yaml_path}")
    assert ssh_connection.get_return_code() == 0, "Failed to create deployment"
    get_logger().log_info(f"Deployment created with {target_pods} replicas pinned to {target_node}")

    get_logger().log_info("Waiting for pods to be scheduled and running")
    pod_getter = KubectlGetPodsKeywords(ssh_connection)
    pod_getter.wait_for_pods_to_reach_status(expected_status="Running", pod_names=["kpi-test-deployment"], namespace=namespace, timeout=300)
    get_logger().log_info(f"All {target_pods} pods are Running on {target_node}")

    return pod_getter


def wait_for_pods_rescheduled(ssh_connection: SSHConnection, namespace: str, failed_node_name: str, expected_count: int, initial_pod_uids: List[str], timeout: int = 600) -> tuple:
    """
    Waits for pods to be rescheduled using pod creation timestamps (not Running status)

    Args:
        ssh_connection (SSHConnection): SSH connection to the controller
        namespace (str): namespace to monitor
        failed_node_name (str): name of the failed node to exclude
        expected_count (int): expected number of pods to be rescheduled
        initial_pod_uids (List[str]): UIDs of original pods to exclude from count
        timeout (int): maximum time to wait in seconds

    Returns:
        tuple: (recovery_time, recovery_time_str, rescheduled_count) when pods are created on other nodes

    """
    start_time = time.time()
    kubeconfig = "export KUBECONFIG=/etc/kubernetes/admin.conf"

    while time.time() - start_time < timeout:
        try:
            output = ssh_connection.send(f"{kubeconfig}; kubectl get pods -n {namespace} -l app=kpi-test -o json")
            if ssh_connection.get_return_code() == 0:
                pods_json = json.loads("".join(output))

                new_pods_on_other_nodes = []
                for pod in pods_json.get("items", []):
                    pod_uid = pod["metadata"]["uid"]
                    pod_name = pod["metadata"]["name"]
                    node_name = pod["spec"].get("nodeName", "")

                    if pod_uid not in initial_pod_uids and node_name and node_name != failed_node_name:
                        new_pods_on_other_nodes.append({"name": pod_name, "node": node_name, "uid": pod_uid})

                if len(new_pods_on_other_nodes) >= expected_count:
                    recovery_time = time.time()
                    recovery_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    get_logger().log_info(f"{len(new_pods_on_other_nodes)} new pods created on other nodes at {recovery_time_str}")
                    return recovery_time, recovery_time_str, len(new_pods_on_other_nodes)
        except json.JSONDecodeError as e:
            get_logger().log_debug(f"JSON decode error: {e}")
        except KeyError as e:
            get_logger().log_debug(f"Missing key in pod data: {e}")

        time.sleep(1)

    raise AssertionError(f"Pods were not rescheduled within {timeout} seconds")


def wait_for_node_status(ssh_connection: SSHConnection, node_name: str, expected_status: str, timeout: int = 600) -> tuple:
    """
    Waits for a node to reach the expected status

    Args:
        ssh_connection (SSHConnection): SSH connection to the controller
        node_name (str): name of the node to monitor
        expected_status (str): expected node status (e.g., "Ready", "NotReady")
        timeout (int): maximum time to wait in seconds

    Returns:
        tuple: (timestamp, timestamp_str) when node reaches expected status, or (None, None) if timeout

    """
    get_logger().log_info(f"Waiting for node {node_name} to reach status: {expected_status}")
    start_time = time.time()
    check_interval = 1

    while time.time() - start_time < timeout:
        try:
            nodes = KubectlNodesKeywords(ssh_connection).get_kubectl_nodes()
            if nodes:
                node = nodes.get_node(node_name)

                if node and node.get_status() == expected_status:
                    status_time = time.time()
                    status_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    get_logger().log_info(f"Node {node_name} reached status {expected_status} at {status_time_str}")
                    return status_time, status_time_str
        except Exception as e:
            get_logger().log_debug(f"Error checking node status: {e}")

        time.sleep(check_interval)

    get_logger().log_info(f"Node {node_name} did not reach status {expected_status} within {timeout} seconds")
    return None, None


def setup_namespace_and_image(ssh_connection: SSHConnection, namespace: str):
    """
    Sets up namespace and prepares busybox image

    Args:
        ssh_connection (SSHConnection): SSH connection to the controller
        namespace (str): namespace to create

    """
    get_logger().log_info("Create namespace for KPI test")
    KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace(namespace)
    KubectlCreateNamespacesKeywords(ssh_connection).create_namespaces(namespace)

    get_logger().log_info("Prepare busybox image in local registry")
    prepare_busybox_image(ssh_connection, namespace)


def label_node(ssh_connection: SSHConnection, node_name: str, label_key: str = "kpi-test-node", label_value: str = "true"):
    """
    Labels a node for pod placement

    Args:
        ssh_connection (SSHConnection): SSH connection to the controller
        node_name (str): name of the node to label
        label_key (str): label key
        label_value (str): label value

    """
    ssh_connection.send(f"source /etc/platform/openrc; export KUBECONFIG=/etc/kubernetes/admin.conf; kubectl label nodes {node_name} {label_key}={label_value} --overwrite")
    assert ssh_connection.get_return_code() == 0, f"Failed to label node {node_name}"


def remove_node_label(ssh_connection: SSHConnection, node_name: str, label_key: str = "kpi-test-node"):
    """
    Removes a label from a node

    Args:
        ssh_connection (SSHConnection): SSH connection to the controller
        node_name (str): name of the node
        label_key (str): label key to remove

    """
    ssh_connection.send(f"source /etc/platform/openrc; export KUBECONFIG=/etc/kubernetes/admin.conf; kubectl label nodes {node_name} {label_key}- --overwrite")


def cleanup_test_resources(ssh_connection: SSHConnection, namespace: str, target_node: str, backup_node: str):
    """
    Cleans up test deployment, namespace, and node labels

    Args:
        ssh_connection (SSHConnection): SSH connection to the controller
        namespace (str): namespace to delete
        target_node (str): target node to remove label from
        backup_node (str): backup node to remove label from

    """
    get_logger().log_info("Cleaning up test deployment and namespace")
    try:
        ssh_connection.send(f"source /etc/platform/openrc; export KUBECONFIG=/etc/kubernetes/admin.conf; kubectl delete deployment kpi-test-deployment -n {namespace} --ignore-not-found=true")
        ssh_connection.send(f"source /etc/platform/openrc; export KUBECONFIG=/etc/kubernetes/admin.conf; kubectl delete namespace {namespace} --ignore-not-found=true")
        if target_node:
            remove_node_label(ssh_connection, target_node)
        if backup_node:
            remove_node_label(ssh_connection, backup_node)
    except Exception as e:
        get_logger().log_info(f"Error during cleanup: {e}")
