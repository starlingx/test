from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.node.kubectl_describe_node_keywords import KubectlDescribeNodeKeywords
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
    dashboard_file_names = ["pod_affinity_controller.yaml", "pod_affinity_compute.yaml"]
    get_logger().log_info("Creating pod_affinity directory")
    FileKeywords(ssh_connection).create_directory(f"/home/sysadmin/{node_affinity_dir}")
    for dashboard_file_name in dashboard_file_names:
        local_path = get_stx_resource_path(f"resources/cloud_platform/containers/node_affinity/{dashboard_file_name}")
        FileKeywords(ssh_connection).upload_file(local_path, f"/home/sysadmin/{node_affinity_dir}/{dashboard_file_name}")

    def teardown():
        get_logger().log_info("Deleting pod_node_affinity directory")
        FileKeywords(ssh_connection).delete_folder_with_sudo(f"/home/sysadmin/{node_affinity_dir}")

    request.addfinalizer(teardown)


@mark.lab_is_aio
def test_node_affinity_controller(request: FixtureRequest):
    """
    Test the functionality of the node affinity to a  controller by applying
    the necessary Kubernetes YAML configuration and verifying the behavior.


    Test Steps:
        Step 1: Transfer the pod affinity files to the active controller (setup)
            - Copy test files from local to the SystemController.
            - Check the copies on the SystemController.
        Step 2: Apply the pod affinity YAML file using kubectl.
        Step 3: Verify the pod affinity behavior(affinity to controller) by checking the status of the pods.
        Step 4: Clean up the test environment by deleting the created resources (teardown).
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    # Step 1: Transfer the dashboard files to the active controller
    get_logger().log_test_case_step("Step 1: Transfer the dashboard files to the active controller")
    pod_name = "node-affinity-to-controller-pod"
    namespace = "test-node-affinity-namespace"
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    copy_affinity_files(request, ssh_connection)
    get_logger().log_info("Running test_node_affinity_controller")

    def teardown():
        # Step 4: Clean up the test environment by deleting the created resources (teardown).
        get_logger().log_test_case_step("Step 4: Clean up the test environment by deleting the created resources (teardown).")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/node_affinity/pod_affinity_controller.yaml")

    request.addfinalizer(teardown)
    get_logger().log_test_case_step("Step 2: Apply the pod affinity YAML file using kubectl.")
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml("/home/sysadmin/node_affinity/pod_affinity_controller.yaml")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
        pod_name=pod_name,
        namespace=namespace,
        expected_status="Running",
        timeout=60,
    )
    get_logger().log_info("Pod (node-affinity-to-controller-pod) is running")
    # Verify the pod affinity behavior by checking the status of the pods
    get_logger().log_test_case_step("Step 3: Verify the pod affinity " "behavior(affinity to controller) by checking the status of the pods")
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods(namespace=namespace)
    node_affinity_pod = pods.get_pod(pod_name)
    assert node_affinity_pod is not None, f"Pod {pod_name} not found"
    get_logger().log_info(f"Pod {node_affinity_pod.get_name()} is running on node {node_affinity_pod.get_node()}")
    pod_node_role = KubectlDescribeNodeKeywords(ssh_connection).describe_node(node_affinity_pod.get_node()).get_node_description().get_roles()
    # check if host has control-plane role, if so, the node is a controller
    assert "control-plane" in pod_node_role, f"Pod {node_affinity_pod.get_name()} is not running on controller host"


@mark.lab_has_compute
def test_node_affinity_compute(request: FixtureRequest):
    """
    Test the functionality of the node affinity to a compute by applying
    the necessary Kubernetes YAML configuration and verifying the behavior.


    Test Steps:
        Step 1: Transfer the pod affinity files to the active controller (setup)
            - Copy test files from local to the SystemController.
            - Check the copies on the SystemController.
        Step 2: Apply the pod affinity YAML file using kubectl.
        Step 3: Verify the pod affinity behavior(affinity to compute) by checking the status of the pods.
        Step 4: Clean up the test environment by deleting the created resources (teardown).
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    # Step 1: Transfer the dashboard files to the active controller
    get_logger().log_test_case_step("Step 1: Transfer the dashboard files to the active controller")
    pod_name = "node-affinity-to-compute-pod"
    namespace = "test-node-affinity-namespace"
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    copy_affinity_files(request, ssh_connection)
    get_logger().log_info("Running test_node_affinity_compute")

    def teardown():
        # Step 4: Clean up the test environment by deleting the created resources (teardown).
        get_logger().log_test_case_step("Step 4: Clean up the test environment by deleting the created resources (teardown).")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/node_affinity/pod_affinity_compute.yaml")

    request.addfinalizer(teardown)
    get_logger().log_test_case_step("Step 2: Apply the pod affinity YAML file using kubectl.")

    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml("/home/sysadmin/node_affinity/pod_affinity_compute.yaml")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
        pod_name=pod_name,
        namespace=namespace,
        expected_status="Running",
        timeout=60,
    )
    get_logger().log_info("Pod (node-affinity-to-compute-pod) is running")
    # Verify the pod affinity behavior by checking the status of the pods
    get_logger().log_test_case_step("Step 3: Verify the pod affinity " "behavior(affinity to compute) by checking the status of the pods")
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods(namespace=namespace)
    node_affinity_pod = pods.get_pod(pod_name)
    assert node_affinity_pod is not None, f"Pod {pod_name} not found"
    get_logger().log_info(f"Pod {node_affinity_pod.get_name()} is running on node {node_affinity_pod.get_node()}")
    pod_node_role = KubectlDescribeNodeKeywords(ssh_connection).describe_node(node_affinity_pod.get_node()).get_node_description().get_roles()
    # check if host has control-plane role, if so, the node is a controller
    assert "control-plane" not in pod_node_role, f"Pod {node_affinity_pod.get_name()} is not running on controller host"
