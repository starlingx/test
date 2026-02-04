import re

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_not_none
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.cat.cat_kernel_core_pattern_keywords import CatKernelCorePatternKeywords
from keywords.k8s.pods.kubectl_create_pods_keywords import KubectlCreatePodsKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords

K8S_COREDUMP_YAML_DIR = "resources/cloud_platform/containers/k8s_coredump"
POD_NAME = "dummypod"
POD_COREDUMP_PATH_ON_HOST = "/var/lib/systemd/coredump"
SLEEP_PROCESS_CREATE_CMDLINE = "nohup sleep 10 > /dev/null 2>&1 &"
SLEEP_PROCESS_KILL_CMDLINE = "pkill -6 -f 'sleep 10'"


@mark.p3
def test_verify_kernel_core_pattern_controller():
    """
    Verify kernel core_pattern after puppet configuration on controller

    Test Steps:
        Step 1: Execute cat /proc/sys/kernel/core_pattern command to retrieve core pattern value in hosts
        Step 2: Check if the expected value is present in the retrieved core pattern
    """
    get_logger().log_test_case_step("Retrieve the core pattern value from file")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    core_pattern = CatKernelCorePatternKeywords(ssh_connection).get_core_pattern()
    get_logger().log_info(f"Core pattern is {core_pattern}")

    get_logger().log_test_case_step("Check if the expected core pattern is present")
    expected_core_pattern = r"\|/usr/bin/k8s-coredump.*[a-zA-Z\d]"
    validate_not_none(re.search(expected_core_pattern, core_pattern), "Kernel core pattern found")


@mark.p3
@mark.lab_has_compute
def test_verify_kernel_core_pattern_compute():
    """
    Verify kernel core_pattern after puppet configuration on compute

    Test Steps:
        Step 1: Execute cat /proc/sys/kernel/core_pattern command to retrieve core pattern value in hosts
        Step 2: Check if the expected value is present in the retrieved core pattern
    """
    get_logger().log_test_case_step("Retrieve the core pattern value from file")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    computes = SystemHostListKeywords(ssh_connection).get_computes()
    compute_ssh_connection = LabConnectionKeywords().get_compute_ssh(computes[0].get_host_name())
    core_pattern = CatKernelCorePatternKeywords(compute_ssh_connection).get_core_pattern()
    get_logger().log_info(f"Core pattern is {core_pattern}")

    get_logger().log_test_case_step("Check if the expected core pattern is present")
    expected_core_pattern = r"\|/usr/bin/k8s-coredump.*[a-zA-Z\d]"
    validate_not_none(re.search(expected_core_pattern, core_pattern), "Kernel core pattern found")


@mark.p3
def test_verify_token_in_k8s_coredump_controller():
    """
    Verify k8s-coredump handler is added on controller and verify service token is configured in the k8s-coredump configuration file

    Test Steps:
        Step 1: Check the presence of the k8s-coredump-conf.json configuration file
        Step 2: Verify that the k8s_coredump_token token is present in the configuration file
    """
    file_path = "/etc/k8s-coredump-conf.json"

    get_logger().log_test_case_step("Check k8s-coredump configuration file on controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    file_keywords = FileKeywords(ssh_connection)
    validate_equals(file_keywords.validate_file_exists_with_sudo(f"{file_path}"), True, "k8s-coredump configuration file found")

    get_logger().log_test_case_step("Verify k8s_coredump_token in configuration file")
    token = file_keywords.read_file_with_sudo(f"{file_path}")
    expected_k8s_coredump_token = r".*\"k8s_coredump_token\":.*[a-zA-Z\d]+.*"
    validate_not_none(re.search(expected_k8s_coredump_token, token[1]), "k8s_coredump_token found in file")


@mark.p3
@mark.lab_has_compute
def test_verify_token_in_k8s_coredump_compute():
    """
    Verify k8s-coredump handler is added on compute and verify service token is configured in the k8s-coredump configuration file

    Test Steps:
        Step 1: Check the presence of the k8s-coredump-conf.json configuration file
        Step 2: Verify that the k8s_coredump_token token is present in the configuration file
    """
    file_path = "/etc/k8s-coredump-conf.json"

    get_logger().log_test_case_step("Check k8s-coredump configuration file on compute")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    computes = SystemHostListKeywords(ssh_connection).get_computes()
    compute_ssh_connection = LabConnectionKeywords().get_compute_ssh(computes[0].get_host_name())
    file_keywords = FileKeywords(compute_ssh_connection)
    validate_equals(file_keywords.validate_file_exists_with_sudo(f"{file_path}"), True, "k8s-coredump configuration file found")

    get_logger().log_test_case_step("Verify k8s_coredump_token in configuration file")
    token = file_keywords.read_file_with_sudo(f"{file_path}")
    expected_k8s_coredump_token = r".*\"k8s_coredump_token\":.*[a-zA-Z\d]+.*"
    validate_not_none(re.search(expected_k8s_coredump_token, token[1]), "k8s_coredump_token found in file")


@mark.p3
def test_verify_coredump_non_k8_apps(request: FixtureRequest):
    """
    Verify core dump file generation on non-Kubernetes host when process crashes.

    Test Steps:
        Step 1: Create a process by sending a sleep command and then crash the process
        Step 2: Check that the core dump file is generated on the host
        Step 3: Remove the core dump file
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    coredump_path = "/var/log/coredump"
    core_file = "core.sleep.*.zst"

    get_logger().log_test_case_step("Create a sleep process and crash it")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ssh_connection.send(SLEEP_PROCESS_CREATE_CMDLINE)
    ssh_connection.send_as_sudo(SLEEP_PROCESS_KILL_CMDLINE)

    get_logger().log_test_case_step(f"Check coredump file generated on host {coredump_path}")
    file_keywords = FileKeywords(ssh_connection)
    validate_equals(file_keywords.validate_file_exists_with_sudo(f"{coredump_path}/{core_file}"), True, "Coredump file was generated on host")

    def teardown():
        get_logger().log_teardown_step(f"Remove coredump file from {coredump_path}")
        file_keywords.delete_file(f"{coredump_path}/{core_file}")

    request.addfinalizer(teardown)


@mark.p1
def test_verify_coredump_using_default_handling(request: FixtureRequest):
    """
    Verify coredump file generation with default handling for k8s pod.

    Test Steps:
        Step 1: Create pod with default config
        Step 2: Create a process by sending a sleep command and then crash the process inside pod
        Step 3: Check that the coredump file is generated on the Kubernetes node where the pod is running
        Step 4: Delete the pod and resources
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    coredump_file = "core.sleep.*.zst"
    filename = "default_k8s_config.yaml"

    get_logger().log_test_case_step("Create pod with default handling")
    lab_connection_keywords = LabConnectionKeywords()
    ssh_connection = lab_connection_keywords.get_active_controller_ssh()

    # Copy yaml file to host
    file_keywords_active_controller = FileKeywords(ssh_connection)
    file_keywords_active_controller.upload_file(get_stx_resource_path(f"{K8S_COREDUMP_YAML_DIR}/{filename}"), f"/home/sysadmin/{filename}")

    # Create pod from yaml and wait for 'Running' status
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(f"/home/sysadmin/{filename}")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pod_status(POD_NAME, "Running")

    def cleanup_pod():
        get_logger().log_teardown_step("Delete pod")
        KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(POD_NAME)
        file_keywords_active_controller.delete_file(f"/home/sysadmin/{filename}")

    request.addfinalizer(cleanup_pod)

    # Generate a coredump inside pod
    get_logger().log_test_case_step("Create coredump inside pod")
    kubectl_exec = KubectlExecInPodsKeywords(ssh_connection)
    kubectl_exec.run_pod_exec_cmd(POD_NAME, SLEEP_PROCESS_CREATE_CMDLINE)
    kubectl_exec.run_pod_exec_cmd(POD_NAME, SLEEP_PROCESS_KILL_CMDLINE)

    # Verify the coredump exists on host
    kubectl_pods.wait_for_pod_status(POD_NAME, "Running")
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods_all_namespaces()
    pod_host = pods.get_pod(POD_NAME).get_node()
    output = kubectl_exec.run_pod_exec_cmd(POD_NAME, f"ls coredump | grep {coredump_file}")
    validate_not_none(output, "Coredump file was generated on pod")
    get_logger().log_test_case_step(f"Check coredump file on host ({pod_host}) where pod is running")
    ssh_pod_host_connection = lab_connection_keywords.get_ssh_for_hostname(pod_host)
    file_keywords = FileKeywords(ssh_pod_host_connection)
    validate_equals(file_keywords.validate_file_exists_with_sudo(f"{POD_COREDUMP_PATH_ON_HOST}/{coredump_file}"), True, f"Coredump file was generated on host {pod_host}")

    def remove_coredump():
        get_logger().log_teardown_step("Remove coredump")
        file_keywords.delete_file(f"{POD_COREDUMP_PATH_ON_HOST}/{coredump_file}")

    request.addfinalizer(remove_coredump)


@mark.p0
def test_verify_coredump_using_full_config_annotations(request: FixtureRequest):
    """
    Verify coredump file generation with full config for k8s pod.

    Test Steps:
        Step 1: Create pod with full config
        Step 2: Create a process by sending a sleep command and then crash the process inside pod
        Step 3: Check that the coredump file is generated on the Kubernetes node where the pod is running
        Step 4: Delete the pod and resources
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    coredump_file = "core.*sleep.lz4"
    filename = "full_k8s_config.yaml"

    get_logger().log_test_case_step("Create pod with full config annotations")
    lab_connection_keywords = LabConnectionKeywords()
    ssh_connection = lab_connection_keywords.get_active_controller_ssh()

    # Copy yaml file to host
    file_keywords_active_controller = FileKeywords(ssh_connection)
    file_keywords_active_controller.upload_file(get_stx_resource_path(f"{K8S_COREDUMP_YAML_DIR}/{filename}"), f"/home/sysadmin/{filename}")

    # Create pod from yaml and wait for 'Running' status
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(f"/home/sysadmin/{filename}")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pod_status(POD_NAME, "Running")

    def cleanup_pod():
        get_logger().log_teardown_step("Delete pod")
        KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(POD_NAME)
        file_keywords_active_controller.delete_file(f"/home/sysadmin/{filename}")

    request.addfinalizer(cleanup_pod)

    # Generate a coredump inside pod
    get_logger().log_test_case_step("Create coredump inside pod")
    kubectl_exec = KubectlExecInPodsKeywords(ssh_connection)
    kubectl_exec.run_pod_exec_cmd(POD_NAME, SLEEP_PROCESS_CREATE_CMDLINE)
    kubectl_exec.run_pod_exec_cmd(POD_NAME, SLEEP_PROCESS_KILL_CMDLINE)

    # Verify the coredump exists on host
    kubectl_pods.wait_for_pod_status(POD_NAME, "Running")
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods_all_namespaces()
    pod_host = pods.get_pod(POD_NAME).get_node()
    output = kubectl_exec.run_pod_exec_cmd(POD_NAME, f"ls coredump | grep {coredump_file}")
    validate_not_none(output, "Coredump file was generated on pod")
    get_logger().log_test_case_step(f"Check coredump file on host ({pod_host}) where pod is running")
    ssh_pod_host_connection = lab_connection_keywords.get_ssh_for_hostname(pod_host)
    file_keywords = FileKeywords(ssh_pod_host_connection)
    validate_equals(file_keywords.validate_file_exists_with_sudo(f"{POD_COREDUMP_PATH_ON_HOST}/{coredump_file}"), True, "Coredump file was generated on host")

    def remove_coredump():
        get_logger().log_teardown_step("Remove coredump")
        file_keywords.delete_file(f"{POD_COREDUMP_PATH_ON_HOST}/{coredump_file}")

    request.addfinalizer(remove_coredump)


@mark.p1
def test_verify_coredump_using_minimal_config_annotations(request: FixtureRequest):
    """
    Verify coredump file generation with minimal config for k8s pod.

    Test Steps:
        Step 1: Create pod with minimal config
        Step 2: Create a process by sending a sleep command and then crash the process inside pod
        Step 3: Check that the coredump file is generated on the Kubernetes node where the pod is running
        Step 4: Delete the pod and resources
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    coredump_file = "core.*sleep"
    filename = "minimal_k8s_config.yaml"

    get_logger().log_test_case_step("Create pod with minimal config annotations")
    lab_connection_keywords = LabConnectionKeywords()
    ssh_connection = lab_connection_keywords.get_active_controller_ssh()

    # Copy yaml file to host
    file_keywords_active_controller = FileKeywords(ssh_connection)
    file_keywords_active_controller.upload_file(get_stx_resource_path(f"{K8S_COREDUMP_YAML_DIR}/{filename}"), f"/home/sysadmin/{filename}")

    # Create pod from yaml and wait for 'Running' status
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(f"/home/sysadmin/{filename}")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pod_status(POD_NAME, "Running")

    def cleanup_pod():
        get_logger().log_teardown_step("Delete pod")
        KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(POD_NAME)
        file_keywords_active_controller.delete_file(f"/home/sysadmin/{filename}")

    request.addfinalizer(cleanup_pod)

    # Generate a coredump inside pod
    get_logger().log_test_case_step("Create coredump inside pod")
    kubectl_exec = KubectlExecInPodsKeywords(ssh_connection)
    kubectl_exec.run_pod_exec_cmd(POD_NAME, SLEEP_PROCESS_CREATE_CMDLINE)
    kubectl_exec.run_pod_exec_cmd(POD_NAME, SLEEP_PROCESS_KILL_CMDLINE)

    # Verify the coredump exists on host
    kubectl_pods.wait_for_pod_status(POD_NAME, "Running")
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods_all_namespaces()
    pod_host = pods.get_pod(POD_NAME).get_node()
    output = kubectl_exec.run_pod_exec_cmd(POD_NAME, f"ls coredump | grep {coredump_file}")
    validate_not_none(output, "Coredump file was generated on pod")
    get_logger().log_test_case_step(f"Check coredump file on host ({pod_host}) where pod is running")
    ssh_pod_host_connection = lab_connection_keywords.get_ssh_for_hostname(pod_host)
    file_keywords = FileKeywords(ssh_pod_host_connection)
    validate_equals(file_keywords.validate_file_exists_with_sudo(f"{POD_COREDUMP_PATH_ON_HOST}/{coredump_file}"), True, "Coredump file was generated on host")

    def remove_coredump():
        get_logger().log_teardown_step("Remove coredump")
        file_keywords.delete_file(f"{POD_COREDUMP_PATH_ON_HOST}/{coredump_file}")

    request.addfinalizer(remove_coredump)
