import ipaddress

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals, validate_not_none, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_label_keywords import SystemHostLabelKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.kube_cpusets.kube_cpusets_keywords import KubeCpusetsKeywords
from keywords.linux.cat.cat_os_keywords import CatOSKeywords

KATA_DIR = '/home/sysadmin/kata'
KATA_YAML_FILES = ['kata-runtime.yaml', 'nginx-kata.yaml', 'non-static-cpu-pod.yaml', 'static-cpu-pod.yaml']


def copy_kata_files(request, ssh_connection: SSHConnection):
    """
    Copy the kata yaml files to the active controller.

    Args:
        request: pytest request object
        ssh_connection (SSHConnection): SSH connection object
    """
    get_logger().log_info("Copying kata runtime yaml files to active controller")
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.create_directory(KATA_DIR)

    local_kata_dir = get_stx_resource_path('resources/cloud_platform/containers/kata')
    for yaml_file in KATA_YAML_FILES:
        file_keywords.upload_file(f"{local_kata_dir}/{yaml_file}", f"{KATA_DIR}/{yaml_file}")

    def teardown():
        get_logger().log_info("Deleting kata directory")
        FileKeywords(ssh_connection).delete_folder_with_sudo(KATA_DIR)

    request.addfinalizer(teardown)


def apply_kata_runtime(request, ssh_connection: SSHConnection):
    """
    Apply the kata runtime class from yaml file.

    Args:
        request: pytest request object
        ssh_connection (SSHConnection): SSH connection object
    """
    runtime_file = f'{KATA_DIR}/kata-runtime.yaml'
    get_logger().log_info(f'Deploy {runtime_file} in active controller')
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(runtime_file)

    def teardown():
        get_logger().log_info(f'Undeploy {runtime_file} in active controller')
        KubectlFileDeleteKeywords(ssh_connection).delete_resources(runtime_file)

    request.addfinalizer(teardown)


def configure_cpu_management_and_topology_policies(request, ssh_connection: SSHConnection):
    """
    Configure CPU management and topology policies in the last available host.

    Args:
        request: pytest request object
        ssh_connection (SSHConnection): SSH connection object
    """
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    all_hosts = host_list_keywords.get_system_host_list().get_hosts()
    hostname = all_hosts[-1].get_host_name()

    get_logger().log_info(
        f'Configure static cpu policy in {hostname} '
        'assigning labels: kube-topology-mgr-policy=restricted and kube-cpu-mgr-policy=static'
    )

    label_keywords = SystemHostLabelKeywords(ssh_connection)

    def teardown():
        get_logger().log_info('Removing labels: kube-cpu-mgr-policy and kube-topology-mgr-policy')
        label_keywords.lock_host_remove_labels_and_unlock(hostname, ['kube-cpu-mgr-policy', 'kube-topology-mgr-policy'])

    request.addfinalizer(teardown)

    label_keywords.lock_host_assign_labels_and_unlock(hostname, ['kube-cpu-mgr-policy=static', 'kube-topology-mgr-policy=restricted'])


def get_kernel_version(ssh_connection: SSHConnection, is_pod: bool = False, pod_name: str = None) -> str:
    """Get kernel version from pod or controller.

    Args:
        ssh_connection (SSHConnection): SSH connection.
        is_pod (bool): True if checks pod else False.
        pod_name (str): Pod name to check.

    Returns:
        str: Kernel version string.
    """
    if is_pod:
        get_logger().log_info(f"Get kernel version from pod {pod_name}")
        os_release_output = KubectlExecInPodsKeywords(ssh_connection).get_os_release(pod_name)
    else:
        get_logger().log_info("Get kernel version from controller")
        os_release_output = CatOSKeywords(ssh_connection).get_os_release()
    return os_release_output.get_version()


@mark.p2
def test_basic_pod_kernel_version(request):
    """
    Verifies that kata pod kernel version differs from host OS kernel version.

    Test Steps:
        - Copy kata runtime files and apply kata runtime class
        - Deploy nginx-kata pod from yaml file
        - Wait for pod to reach Running status
        - Get OS release version from active controller
        - Get OS release version from nginx-kata pod
        - Validate pod kernel version differs from host kernel version
    """
    pod_name = 'nginx-kata'
    nginx_kata_file = f'{KATA_DIR}/nginx-kata.yaml'

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step('Copy kata files and apply kata runtime')
    copy_kata_files(request, ssh_connection)
    apply_kata_runtime(request, ssh_connection)

    get_logger().log_test_case_step(f'Deploy {nginx_kata_file} in active controller')
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(nginx_kata_file)

    def teardown():
        get_logger().log_teardown_step(f'Delete pod {pod_name}')
        ssh_conn = LabConnectionKeywords().get_active_controller_ssh()
        KubectlDeletePodsKeywords(ssh_conn).delete_pod(pod_name)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f'Wait for {pod_name} to be in RUNNING status')
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    validate_equals(pods_keywords.wait_for_pods_to_reach_status("Running", pod_names=[pod_name]), True, f"{pod_name} is in Running status")

    get_logger().log_test_case_step("Get os-release version from active controller")
    os_kernel_version = get_kernel_version(ssh_connection)

    get_logger().log_test_case_step(f"Get os-release version from {pod_name}")
    pod_kernel_version = get_kernel_version(ssh_connection, is_pod=True, pod_name=pod_name)

    validate_not_equals(pod_kernel_version, os_kernel_version, 'Kata pod kernel version should differ from host OS kernel version')


@mark.p2
def test_kata_containers_non_static_cpu_policy(request):
    """
    Verifies besteffort QoS assignment for a kata container with non-static cpu policy.

    Test Steps:
        - Copy kata runtime files and apply kata runtime class
        - Deploy non-static-cpu pod from yaml file
        - Wait for pod to reach Running status
        - Identify pod host node
        - Get kube-cpusets information from pod host
        - Validate QoS is besteffort for the pod
    """
    pod_name = 'non-static-cpu-pod'
    non_static_cpu_file = f'{KATA_DIR}/{pod_name}.yaml'

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step('Copy kata files and apply kata runtime')
    copy_kata_files(request, ssh_connection)
    apply_kata_runtime(request, ssh_connection)

    get_logger().log_test_case_step(f'Deploy {non_static_cpu_file} in active controller')
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(non_static_cpu_file)

    def teardown():
        get_logger().log_teardown_step(f'Delete pod {pod_name}')
        ssh_conn = LabConnectionKeywords().get_active_controller_ssh()
        KubectlDeletePodsKeywords(ssh_conn).delete_pod(pod_name)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f'Wait for {pod_name} to be in RUNNING status')
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    validate_equals(pods_keywords.wait_for_pods_to_reach_status("Running", pod_names=[pod_name]), True, f"{pod_name} is in Running status")

    # Get pod host
    pod_host = pods_keywords.get_pods().get_pod(pod_name).get_node()

    get_logger().log_test_case_step(f'Get kube-cpusets for {pod_name} on {pod_host}')
    host_ssh = LabConnectionKeywords().get_ssh_for_hostname(pod_host)
    cpusets_keywords = KubeCpusetsKeywords(host_ssh)
    cpusets_output = cpusets_keywords.get_kube_cpusets_output()

    get_logger().log_test_case_step(f'Validate QoS is besteffort for {pod_name}')
    containers = cpusets_output.get_containers_by_pod_name(pod_name)
    pod_qos = containers[0].get_qos() if containers else None

    validate_not_none(pod_qos, f"QoS found for {pod_name}")
    validate_str_contains(pod_qos.lower(), 'besteffort', f"{pod_name} has besteffort QoS")


@mark.p2
def test_kata_containers_static_cpu_policy(request):
    """
    Verifies guaranteed QoS assignment for a kata container with static cpu policy.

    Test Steps:
        - Copy kata runtime files and apply kata runtime class
        - Configure CPU management and topology policies on host
        - Deploy static-cpu pod from yaml file
        - Wait for pod to reach Running status
        - Identify pod host node
        - Get kube-cpusets information from pod host
        - Validate QoS is guaranteed for the pod
    """
    pod_name = 'static-cpu-pod'
    static_cpu_file = f'{KATA_DIR}/{pod_name}.yaml'

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step('Copy kata files and apply kata runtime')
    copy_kata_files(request, ssh_connection)
    apply_kata_runtime(request, ssh_connection)
    get_logger().log_test_case_step('Configure CPU management and topology policies')
    configure_cpu_management_and_topology_policies(request, ssh_connection)

    get_logger().log_test_case_step(f'Deploy {static_cpu_file} in active controller')
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(static_cpu_file)

    def teardown():
        get_logger().log_teardown_step(f'Delete pod {pod_name}')
        ssh_conn = LabConnectionKeywords().get_active_controller_ssh()
        KubectlDeletePodsKeywords(ssh_conn).delete_pod(pod_name)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f'Wait for {pod_name} to be in RUNNING status')
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    validate_equals(pods_keywords.wait_for_pods_to_reach_status("Running", pod_names=[pod_name]), True, f"{pod_name} is in Running status")

    # Get pod host
    pod_host = pods_keywords.get_pods().get_pod(pod_name).get_node()

    get_logger().log_test_case_step(f'Get kube-cpusets for {pod_name} on {pod_host}')
    host_ssh = LabConnectionKeywords().get_ssh_for_hostname(pod_host)
    cpusets_keywords = KubeCpusetsKeywords(host_ssh)
    cpusets_output = cpusets_keywords.get_kube_cpusets_output()

    get_logger().log_test_case_step(f'Validate QoS is guaranteed for {pod_name}')
    containers = cpusets_output.get_containers_by_pod_name(pod_name)
    pod_qos = containers[0].get_qos() if containers else None

    validate_not_none(pod_qos, f"QoS found for {pod_name}")
    validate_str_contains(pod_qos.lower(), 'guaranteed', f"{pod_name} has guaranteed QoS")


@mark.p2
@mark.lab_is_ipv6
def test_kata_containers_ipv6_support(request):
    """
    Verifies IPv6 address is correctly assigned inside a kata container.

    Test Steps:
        - Copy kata runtime files to active controller
        - Apply kata runtime class configuration
        - Deploy non-static-cpu pod from yaml file
        - Wait for pod to reach Running status
        - Get pod IPv6 address from kubectl
        - Validate IPv6 address is configured inside the pod
    """
    pod_name = 'non-static-cpu-pod'
    non_static_cpu_file = f'{KATA_DIR}/{pod_name}.yaml'

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step('Copy kata files and apply kata runtime')
    copy_kata_files(request, ssh_connection)
    apply_kata_runtime(request, ssh_connection)

    get_logger().log_test_case_step(f'Deploy {non_static_cpu_file} in active controller')
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(non_static_cpu_file)

    def teardown():
        get_logger().log_teardown_step(f'Delete pod {pod_name}')
        ssh_conn = LabConnectionKeywords().get_active_controller_ssh()
        KubectlDeletePodsKeywords(ssh_conn).delete_pod(pod_name)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f'Wait for {pod_name} to be in RUNNING status')
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    validate_equals(pods_keywords.wait_for_pods_to_reach_status("Running", pod_names=[pod_name]), True, f"{pod_name} is in Running status")

    get_logger().log_test_case_step(f'Get {pod_name} IPv6 address')
    pod_ip = pods_keywords.get_pods().get_pod(pod_name).get_ip()

    get_logger().log_test_case_step('Check pod IPv6 address inside pod')
    output = KubectlExecInPodsKeywords(ssh_connection).get_if_inet6(pod_name)

    # /proc/net/if_inet6 shows fully expanded addresses without colons
    pod_ip_expanded = f'{int(ipaddress.ip_address(pod_ip)):032x}'
    validate_str_contains(''.join(output), pod_ip_expanded, f'Pod IPv6 address {pod_ip} is configured in pod')
