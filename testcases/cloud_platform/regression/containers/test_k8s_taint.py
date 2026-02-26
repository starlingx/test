from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_greater_than_or_equal, validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.node.kubectl_node_taint_keywords import KubectlNodeTaintKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


@mark.p0
@mark.lab_has_worker
def test_taints_enabled():
    """
    Verifies that taints are enabled by default.

    Test Steps:
        - Check if taints are enabled by default
    """
    get_logger().log_test_case_step("Check if taints are enabled")
    
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    
    get_logger().log_info("Verify if taints are enabled on both nodes")
    taint_keywords = KubectlNodeTaintKeywords(ssh_connection)
    taint_output = taint_keywords.get_node_taints()

    expected_taint_keys = [
        'node-role.kubernetes.io/master',
        'node-role.kubernetes.io/control-plane',
    ]
    
    taint_count = sum(taint_output.count_taints(key) for key in expected_taint_keys)
    
    validate_greater_than_or_equal(taint_count, 2, "Taints are enabled by default on controller nodes")


@mark.p1
@mark.lab_has_standby_controller
def test_taint_swact(request):
    """
    Verifies that pods are running/completed after swact.

    Test Steps:
        - Validate controller's status
        - Perform swact
        - Lock/unlock of standby controller
        - Check pods status
    """
    get_logger().log_test_case_step("Make swact and validate pods status")
    
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    
    # Get controllers and validate we have 2
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    controllers_list = host_list_keywords.get_controllers()
    
    # Validate controllers status
    validate_equals(len(controllers_list), 2, "System has exactly 2 controllers")
    
    # Swact active controller
    active_controller = host_list_keywords.get_active_controller()
    get_logger().log_info(f"{active_controller.get_host_name()} is active controller, swact first before attempt to lock")
    
    swact_keywords = SystemHostSwactKeywords(ssh_connection)
    swact_keywords.host_swact()
    
    def swact_rollback():
        ssh_conn = LabConnectionKeywords().get_active_controller_ssh()
        SystemHostSwactKeywords(ssh_conn).host_swact()
    
    request.addfinalizer(swact_rollback)
    
    standby_controller = host_list_keywords.get_standby_controller()
    lock_keywords = SystemHostLockKeywords(ssh_connection)
    
    get_logger().log_info(f"Locking {standby_controller.get_host_name()} the standby controller")
    lock_keywords.lock_host(standby_controller.get_host_name())
    
    get_logger().log_info(f"Unlocking {standby_controller.get_host_name()} the standby controller")
    lock_keywords.unlock_host(standby_controller.get_host_name())
    
    get_logger().log_info("Checking pods are running or completed")
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    pods_status = pods_keywords.wait_for_all_pods_status(["Running", "Completed"], timeout=300)
    validate_equals(pods_status, True, "All pods are in Running or Completed status after swact")


@mark.p1
@mark.lab_has_worker
def test_pod_without_toleration(request):
    """
    Create pod without toleration to be scheduled on a worker node.

    Test Steps:
        - Apply nginx pod YAML without tolerations from resources
        - Verify pod reaches Running status
    """
    POD_NAME = 'nginx-site'
    REMOTE_YAML_PATH = '/tmp/nginx_pod.yaml'
    
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    local_yaml_path = get_stx_resource_path('resources/cloud_platform/containers/nginx_pod.yaml')
    
    get_logger().log_test_case_step("Create pod without tolerations")
    
    # Copy YAML file to remote system
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(local_yaml_path, REMOTE_YAML_PATH)
    
    kubectl_apply = KubectlFileApplyKeywords(ssh_connection)
    kubectl_apply.apply_resource_from_yaml(REMOTE_YAML_PATH)
    
    def cleanup_pod():
        ssh_conn = LabConnectionKeywords().get_active_controller_ssh()
        KubectlDeletePodsKeywords(ssh_conn).delete_pod(POD_NAME)
        FileKeywords(ssh_conn).delete_file(REMOTE_YAML_PATH)
    
    request.addfinalizer(cleanup_pod)
    
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    pod_status = pods_keywords.wait_for_pods_to_reach_status("Running", pod_names=[POD_NAME])
    validate_equals(pod_status, True, f"Pod {POD_NAME} reached Running status")


@mark.p1
@mark.lab_has_worker
def test_pod_with_toleration(request):
    """
    Create pod with toleration and nodeselector to be scheduled on a control-plane node.

    Test Steps:
        - Apply nginx pod YAML with control-plane toleration and node selector from resources
        - Verify pod reaches Running status on control-plane node
    """
    POD_NAME = 'nginx-site'
    REMOTE_YAML_PATH = '/tmp/nginx_pod_with_toleration.yaml'
    
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    local_yaml_path = get_stx_resource_path('resources/cloud_platform/containers/nginx_pod_with_toleration.yaml')
    
    get_logger().log_test_case_step("Create pod with tolerations")
    
    # Copy YAML file to remote system
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(local_yaml_path, REMOTE_YAML_PATH)
    
    kubectl_apply = KubectlFileApplyKeywords(ssh_connection)
    kubectl_apply.apply_resource_from_yaml(REMOTE_YAML_PATH)
    
    def cleanup_pod():
        ssh_conn = LabConnectionKeywords().get_active_controller_ssh()
        KubectlDeletePodsKeywords(ssh_conn).delete_pod(POD_NAME)
        FileKeywords(ssh_conn).delete_file(REMOTE_YAML_PATH)
    
    request.addfinalizer(cleanup_pod)
    
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    pod_status = pods_keywords.wait_for_pods_to_reach_status("Running", pod_names=[POD_NAME])
    validate_equals(pod_status, True, f"Pod {POD_NAME} with toleration reached Running status on control-plane node")
