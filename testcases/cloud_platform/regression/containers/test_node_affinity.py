from pytest import FixtureRequest

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


def copy_affinity_files(request: FixtureRequest, ssh_connection: SSHConnection):
    """
    Copy the necessary node_affinity dashboard yaml files

    Args:
        request (FixtureRequest): pytest fixture
        ssh_connection (SSHConnection): ssh connection object
    """
    node_affinity_dir = "node_affinity"
    dashboard_file_names = ["pod_affinity_controller.yaml"]
    get_logger().log_info("Creating pod_affinity directory")
    FileKeywords(ssh_connection).create_directory(f"/home/sysadmin/{node_affinity_dir}")
    for dashboard_file_name in dashboard_file_names:
        local_path = get_stx_resource_path(f"resources/cloud_platform/containers/node_affinity/{dashboard_file_name}")
        FileKeywords(ssh_connection).upload_file(local_path, f"/home/sysadmin/{node_affinity_dir}/{dashboard_file_name}")

    def teardown():
        get_logger().log_info("Deleting pod_node_affinity directory")
        FileKeywords(ssh_connection).delete_folder_with_sudo(f"/home/sysadmin/{node_affinity_dir}")

    request.addfinalizer(teardown)


def test_node_affinity_controller(request: FixtureRequest):
    """
    Test the functionality of the node affinity controller by applying
    the necessary Kubernetes YAML configuration and verifying the behavior.


    Test Steps:
        Step 1: Transfer the pod affinity files to the active controller (setup)
            - Copy test files from local to the SystemController.
            - Check the copies on the SystemController.
        Step 2: Apply the pod affinity YAML file using kubectl.
        Step 3: Verify the pod affinity behavior by checking the status of the pods.
        Step 4: Clean up the test environment by deleting the created resources (teardown).
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    # Step 1: Transfer the dashboard files to the active controller

    # Defines dashboard file name, source (local) and destination (remote) file paths.
    # Opens an SSH session to active controller.
    pod_name = "node-affinity-to-controller-pod"
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    copy_affinity_files(request, ssh_connection)
    get_logger().log_info("Running test_node_affinity_controller")

    def teardown():
        # Step 4: Clean up the test environment by deleting the created resources (teardown).
        get_logger().log_info("Deleting test pods")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/node_affinity/pod_affinity_controller.yaml")

    request.addfinalizer(teardown)
    # For example, you can run the copied yaml file using kubectl command
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml("/home/sysadmin/node_affinity/pod_affinity_controller.yaml")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
        pod_name=pod_name,
        namespace="default",
        expected_status="Running",
        timeout=60,
    )
    get_logger().log_info("Pod (node-affinity-to-controller-pod) is running")
    # Verify the pod affinity behavior by checking the status of the pods
    get_logger().log_info("Verifying the pod affinity behavior")
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods()
    node_affinity_pod = pods.get_pod(pod_name)
    assert node_affinity_pod is not None, f"Pod {pod_name} not found"
    get_logger().log_info(f"Pod {node_affinity_pod.get_name()} is running on node {node_affinity_pod.get_node()}")
    assert "controller" in node_affinity_pod.get_node(), f"Pod {node_affinity_pod.get_name()} is not running on controller host"
