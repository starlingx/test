from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from framework.web.webdriver_core import WebDriverCore
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.docker.images.docker_load_image_keywords import DockerLoadImageKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.linux.grep.grep_keywords import GrepKeywords
from web_pages.horizon.admin.platform.horizon_fault_management_page import HorizonFaultManagementPage
from web_pages.horizon.login.horizon_login_page import HorizonLoginPage

POD_NAME = "stress-ng"
POD_YAML_RESOURCE = "resources/cloud_platform/containers/stress-ng.yaml"
REMOTE_POD_YAML_PATH = "/home/sysadmin/stress-ng.yaml"
STRESS_NG_IMAGE_TAR = "resources/images/stress-ng.tar"
STRESS_NG_IMAGE_NAME = "alexeiled/stress-ng:latest"
STRESS_NG_REGISTRY_TAG = "stress-ng"
MEMORY_ALARM_ID = "100.103"
MEMORY_ALARM_REASON_TEXT = ".*Memory threshold exceeded ; *threshold.*"


def prepare_stress_ng_image(ssh_connection: SSHConnection) -> None:
    """Load the stress-ng image into the local Docker registry.

    Uploads the stress-ng tar from resources, loads it into Docker,
    tags it for the local registry, pushes it, and creates the
    imagePullSecret needed by the pod.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """
    get_logger().log_test_case_step("Load stress-ng image into local registry")
    local_registry = ConfigurationManager.get_docker_config().get_local_registry()
    file_keywords = FileKeywords(ssh_connection)
    docker_load_keywords = DockerLoadImageKeywords(ssh_connection)

    local_tar_path = get_stx_resource_path(STRESS_NG_IMAGE_TAR)
    remote_tar_path = "/home/sysadmin/stress-ng.tar"
    file_keywords.upload_file(local_tar_path, remote_tar_path, overwrite=False)
    docker_load_keywords.load_docker_image_to_host(remote_tar_path)
    docker_load_keywords.tag_docker_image_for_registry(STRESS_NG_IMAGE_NAME, STRESS_NG_REGISTRY_TAG, local_registry)
    docker_load_keywords.push_docker_image_to_registry(STRESS_NG_REGISTRY_TAG, local_registry)

    get_logger().log_test_case_step("Create registry secret for image pull")
    KubectlCreateSecretsKeywords(ssh_connection).create_secret_for_registry(local_registry, "local-secret")


def deploy_stress_ng_pod(ssh_connection: SSHConnection, alloc: str) -> str:
    """Deploy the stress-ng pod with the specified memory allocation.

    Uploads the stress-ng.yaml resource, replaces the PLACEHOLDER with
    the actual memory allocation, applies it, and waits for it to be Running.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        alloc (str): Memory allocation string (e.g., '1234567k').

    Returns:
        str: The name of the node where the pod is running.
    """
    get_logger().log_test_case_step("Upload stress-ng.yaml to active controller")
    file_keywords = FileKeywords(ssh_connection)
    local_yaml_path = get_stx_resource_path(POD_YAML_RESOURCE)
    file_keywords.upload_file(local_yaml_path, REMOTE_POD_YAML_PATH)

    get_logger().log_test_case_step(f"Configure stress-ng pod with memory allocation: {alloc}")
    ssh_connection.send(f"sed -i 's/PLACEHOLDER/{alloc}/' {REMOTE_POD_YAML_PATH}")

    get_logger().log_test_case_step("Deploy stress-ng pod")
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(REMOTE_POD_YAML_PATH)

    get_logger().log_test_case_step(f"Wait for pod {POD_NAME} to reach Running status")
    validate_equals(
        KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(POD_NAME, "Running", namespace="default", timeout=120),
        True,
        f"Pod {POD_NAME} reached Running status",
    )

    get_logger().log_test_case_step("Get the node where the stress-ng pod is running")
    pods_output = KubectlGetPodsKeywords(ssh_connection).get_pods(namespace="default")
    pod_node = pods_output.get_pod(POD_NAME).get_node()
    get_logger().log_info(f"Pod {POD_NAME} is running on node: {pod_node}")

    return pod_node


def calculate_memory_allocation(ssh_connection: SSHConnection) -> str:
    """Calculate the memory allocation needed to exceed 91% usage on the host.

    Reads MemTotal and MemAvailable from /proc/meminfo and computes
    the additional memory needed to push usage past the 91% threshold.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        str: Memory allocation string with 'k' suffix (e.g., '1234567k').
    """
    get_logger().log_test_case_step("Calculate memory allocation to exceed 91% threshold")
    grep_keywords = GrepKeywords(ssh_connection)
    total = grep_keywords.grep_and_extract_fields("MemTotal", "/proc/meminfo", field_indices=[2])
    avail = grep_keywords.grep_and_extract_fields("MemAvailable", "/proc/meminfo", field_indices=[2])

    alloc = f"{int(int(total) * 0.91 - (int(total) - int(avail)))}k"
    get_logger().log_info(f"Memory total: {total}k, available: {avail}k, allocation for stress: {alloc}")
    return alloc


@mark.p2
def test_memory_alarm_threshold(request: FixtureRequest):
    """Verify that memory usage alarm is raised and cleared when memory stress is applied and removed.

    Test Steps:
        - Load stress-ng image into local registry
        - Calculate the memory allocation needed to exceed 91% usage on the host
        - Validate memory alarm (100.103) is not already present
        - Deploy stress-ng pod with the calculated memory allocation
        - Verify that the memory threshold alarm (100.103) is raised
        - Delete the stress-ng pod to release memory
        - Verify that the memory threshold alarm is cleared

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Register teardown to clean up the pod
    def cleanup():
        """Clean up the stress-ng pod."""
        get_logger().log_teardown_step(f"Delete pod {POD_NAME} if it exists")
        KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(POD_NAME)

    request.addfinalizer(cleanup)

    prepare_stress_ng_image(ssh_connection)
    alloc = calculate_memory_allocation(ssh_connection)

    # Validate memory alarm is not already present before applying stress
    get_logger().log_test_case_step("Validate memory alarm is not present before applying stress")
    alarm_keywords = AlarmListKeywords(ssh_connection)
    validate_equals(
        alarm_keywords.is_alarm_present(MEMORY_ALARM_ID),
        False,
        f"Memory alarm {MEMORY_ALARM_ID} must not be present before stress is applied",
    )

    pod_node = deploy_stress_ng_pod(ssh_connection, alloc)

    # Wait for memory threshold alarm to appear
    get_logger().log_test_case_step("Wait for memory threshold alarm to appear")
    expected_alarm = AlarmListObject()
    expected_alarm.set_alarm_id(MEMORY_ALARM_ID)
    expected_alarm.set_reason_text(MEMORY_ALARM_REASON_TEXT)

    alarm_keywords.set_timeout_in_seconds(600)
    matched_alarms = alarm_keywords.wait_for_alarms_to_appear([expected_alarm])
    get_logger().log_info(f"Memory alarm {MEMORY_ALARM_ID} was successfully raised")

    # Delete the stress-ng pod to release memory
    get_logger().log_test_case_step(f"Delete pod {POD_NAME} to release memory pressure")
    KubectlDeletePodsKeywords(ssh_connection).delete_pod(POD_NAME)

    # Wait for the memory alarm to clear
    get_logger().log_test_case_step("Wait for memory threshold alarm to clear")
    alarm_keywords.set_timeout_in_seconds(600)
    alarm_keywords.wait_for_alarms_cleared(matched_alarms)
    get_logger().log_info(f"Memory alarm {MEMORY_ALARM_ID} was successfully cleared")


@mark.p2
def test_memory_alarm_threshold_gui(request: FixtureRequest):
    """Verify memory usage alarm appears and clears on the Horizon GUI Active Alarms page.

    Test Steps:
        - Login to Horizon as admin
        - Load stress-ng image into local registry
        - Calculate the memory allocation needed to exceed 91% usage on the host
        - Validate memory alarm (100.103) is not already present
        - Deploy stress-ng pod with the calculated memory allocation
        - Navigate to Fault Management Active Alarms page and verify alarm (100.103) appears
        - Delete the stress-ng pod to release memory
        - Verify the alarm disappears from the Active Alarms page

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Setup WebDriver and register teardown
    driver = WebDriverCore()

    def cleanup():
        """Clean up the stress-ng pod and close the browser."""
        get_logger().log_teardown_step(f"Delete pod {POD_NAME} if it exists")
        KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(POD_NAME)
        get_logger().log_teardown_step("Close browser")
        driver.quit()

    request.addfinalizer(cleanup)

    # Login to Horizon
    get_logger().log_test_case_step("Login to Horizon as admin")
    login_page = HorizonLoginPage(driver)
    login_page.navigate_to_login_page()
    login_page.login_as_admin()

    prepare_stress_ng_image(ssh_connection)
    alloc = calculate_memory_allocation(ssh_connection)

    # Validate memory alarm is not already present before applying stress
    get_logger().log_test_case_step("Validate memory alarm is not present before applying stress")
    alarm_keywords = AlarmListKeywords(ssh_connection)
    validate_equals(
        alarm_keywords.is_alarm_present(MEMORY_ALARM_ID),
        False,
        f"Memory alarm {MEMORY_ALARM_ID} must not be present before stress is applied",
    )

    deploy_stress_ng_pod(ssh_connection, alloc)

    # Navigate to Active Alarms page and wait for alarm to appear
    get_logger().log_test_case_step("Navigate to Active Alarms page and wait for memory alarm to appear")
    fault_management_page = HorizonFaultManagementPage(driver)
    fault_management_page.navigate_to_active_alarms_page()
    fault_management_page.wait_for_alarm_to_appear(MEMORY_ALARM_ID)
    get_logger().log_info(f"Memory alarm {MEMORY_ALARM_ID} is visible on Horizon Active Alarms page")

    # Delete the stress-ng pod to release memory
    get_logger().log_test_case_step(f"Delete pod {POD_NAME} to release memory pressure")
    KubectlDeletePodsKeywords(ssh_connection).delete_pod(POD_NAME)

    # Wait for the alarm to clear on the GUI
    get_logger().log_test_case_step("Wait for memory alarm to clear on Active Alarms page")
    fault_management_page.wait_for_alarm_to_clear(MEMORY_ALARM_ID)
    get_logger().log_info(f"Memory alarm {MEMORY_ALARM_ID} cleared from Horizon Active Alarms page")
