"""
Test suite for isolated CPU exhaust and recover scenarios.
"""

from framework.validation.validation import validate_equals, validate_greater_than_or_equal
from pytest import mark, fail

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.containers.isolcpus.isolcpu_keywords import IsolcpuKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.objects.system_host_cpu_output import SystemHostCPUOutput
from keywords.cloud_platform.system.host.system_host_cpu_keywords import SystemHostCPUKeywords
from keywords.cloud_platform.system.host.system_host_label_keywords import SystemHostLabelKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.node.kubectl_describe_node_keywords import KubectlDescribeNodeKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.process_status.process_status_args_keywords import ProcessStatusArgsKeywords


def _get_worker_host(ssh_connection: SSHConnection, request) -> str:
    """
    Get the first worker host that has at least 3 allocatable isolcpus.
    If no worker has sufficient isolcpus configured, configure 3 isolated cores on the first worker
    and register a teardown finalizer to restore the original configuration.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        request: pytest request object to register teardown finalizer.

    Returns:
        str: hostname of the first worker with sufficient allocatable isolcpus
    """
    logger = get_logger()
    workers = SystemHostListKeywords(ssh_connection).get_workers()

    for worker in workers:
        host = worker.get_host_name()
        allocatable = KubectlDescribeNodeKeywords(ssh_connection).describe_node(host)\
            .get_node_description().get_allocatable().get_windriver_isolcpus()
        if allocatable >= 3:
            # Host already has sufficient isolcpus (at least 3) configured for test requirements
            return host

    # No worker has sufficient isolcpus (at least 3), configure 3 isolated cores on first worker
    host = workers[0].get_host_name()
    logger.log_info(f"No worker has sufficient isolcpus (at least 3). Configuring 3 isolated CPUs on {host}")

    # Get current configuration before modifying to restore it later in teardown
    host_cpu_output = SystemHostCPUKeywords(ssh_connection).get_system_host_cpu_list(host)
    original_isolcpus = host_cpu_output.get_number_of_logical_cores(
        processor_id=0, assigned_function='Application-isolated')

    # Lock the host before modifying CPU configuration
    logger.log_info(f"Locking {host} to modify CPU configuration")
    SystemHostLockKeywords(ssh_connection).lock_host(host)

    # Modify CPU configuration to set 3 cores as application-isolated on processor 0
    SystemHostCPUKeywords(ssh_connection).system_host_cpu_modify(
        hostname=host, function='application-isolated', num_cores_on_processor_0=3)

    # Unlock the host to apply the changes
    logger.log_info(f"Unlocking {host} to apply CPU configuration")
    SystemHostLockKeywords(ssh_connection).unlock_host(host)

    # Register teardown to restore original configuration
    def restore_isolcpus():
        if original_isolcpus != 3:
            logger.log_teardown_step(f"Restore original isolated cores configuration on {host}")
            SystemHostLockKeywords(ssh_connection).lock_host(host)
            SystemHostCPUKeywords(ssh_connection).system_host_cpu_modify(
                hostname=host, function='application-isolated', num_cores_on_processor_0=original_isolcpus)
            SystemHostLockKeywords(ssh_connection).unlock_host(host)

    request.addfinalizer(restore_isolcpus)

    return host


def _configure_topology_manager_policy(ssh_connection: SSHConnection, host: str, policy: str) -> None:
    """
    Configure topology manager policy on a worker host if not already set.

    This function checks if the desired topology manager policy is already configured on the host.
    If not, it locks the host, assigns the topology manager policy label, unlocks the host,
    and validates that the policy is active.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        host (str): hostname of the worker node.
        policy (str): desired topology manager policy (none, best-effort, restricted, single-numa-node).
    """
    logger = get_logger()
    logger.log_setup_step(f"Configure '{policy}' topology-manager-policy on {host}")

    # Get current kubelet arguments to check if policy is already configured
    worker_ssh_connection = LabConnectionKeywords().get_ssh_for_hostname(host)
    kubelet_args = ProcessStatusArgsKeywords(worker_ssh_connection).get_process_arguments_as_string("kubelet")

    # Check if the desired policy is already configured
    if f"--topology-manager-policy={policy}" in kubelet_args:
        logger.log_info(f"Topology policy '{policy}' is already configured on {host}")
        return

    # Policy needs to be configured - lock the host before making changes
    logger.log_info(f"Setting topology policy to '{policy}' on {host}")

    if not SystemHostLockKeywords(ssh_connection).is_host_locked(host):
        SystemHostLockKeywords(ssh_connection).lock_host(host)

    # Assign the topology manager policy label to the host
    SystemHostLabelKeywords(ssh_connection).system_host_label_assign(
        host, f"kube-topology-mgr-policy={policy}", overwrite=True)

    # Unlock the host to apply the changes and restart kubelet
    SystemHostLockKeywords(ssh_connection).unlock_host(host)

    # Verify the policy is active by checking kubelet arguments
    logger.log_setup_step(f"Verify {policy} topology policy is active on {host}")
    worker_ssh_connection = LabConnectionKeywords().get_ssh_for_hostname(host)
    ProcessStatusArgsKeywords(worker_ssh_connection).validate_kubelet_topology_manager_policy(host, policy)


def _create_isolcpu_pod_yaml(ssh_connection: SSHConnection, podname: str, num_cpus: int, host: str) -> str:
    """
    Render the isolcpu pod template and upload it to the remote host.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        podname (str): name to assign to the pod and its container.
        num_cpus (int): number of windriver.com/isolcpus to request and limit.
        host (str): node name to pin the pod to via nodeName.

    Returns:
        str: absolute path of the uploaded YAML file on the remote host.
    """
    isolcpu_pod_template = get_stx_resource_path(
        "resources/cloud_platform/containers/isolcpus/isolcpu_pod.yaml")
    replacement = {"pod_name": podname, "num_cpus": num_cpus, "host_name": host}
    test_files_dir = "/home/sysadmin/isolcpus/test_files/"
    FileKeywords(ssh_connection).create_directory(test_files_dir)
    return YamlKeywords(ssh_connection).generate_yaml_file_from_template(
        isolcpu_pod_template, replacement, f"{podname}.yaml", test_files_dir)


def _deploy_isolcpu_pod(ssh_connection: SSHConnection, podname: str, filename: str, num_cpus: int) -> None:
    """
    Deploy an isolcpu pod from YAML and wait for it to reach Running state.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        podname (str): name of the pod to create.
        filename (str): path to the rendered YAML file on the remote host.
        num_cpus (int): number of isolcpus requested by the pod.
    """
    logger = get_logger()
    logger.log_test_case_step(f"Create pod {podname} requesting {num_cpus} isolcpus")

    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(filename)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
        pod_name=podname, expected_status="Running", timeout=300)


def _verify_isolcpu_resource_accounting(
        ssh_connection: SSHConnection, host: str,
        expected_allocatable: int, expected_allocated: int) -> None:
    """
    Verify allocatable and allocated isolcpu resource counts on a node.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        host (str): hostname of the worker node.
        expected_allocatable (int): expected allocatable isolcpus (unchanged).
        expected_allocated (int): expected allocated isolcpus after pod starts.
    """
    isolcpu_keywords = IsolcpuKeywords(ssh_connection)
    isolcpu_keywords.validate_isolcpus_allocatable(host, expected_allocatable)
    isolcpu_keywords.validate_isolcpus_allocated(host, expected_allocated)


def _verify_pod_cpu_assignment(
        ssh_connection: SSHConnection, host: str, podname: str, topo_mgr_policy: str) -> None:
    """
    Verify pod CPU assignment including NUMA affinity and HT sibling pairing.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        host (str): hostname of the worker node.
        podname (str): name of the pod to check.
        topo_mgr_policy (str): topology manager policy (e.g. 'best-effort', 'single-numa-node').
    """
    # Instantiate keyword objects as needed
    isolcpu_keywords = IsolcpuKeywords(ssh_connection)
    worker_ssh_connection = LabConnectionKeywords().get_ssh_for_hostname(host)
    host_cpu_output = SystemHostCPUKeywords(ssh_connection).get_system_host_cpu_list(host)

    # Get processor IDs that the pod's CPUs belong to
    procs = isolcpu_keywords.get_pod_affinity_context(
        worker_ssh_connection, podname, host_cpu_output)

    # Validate single NUMA node for policies that enforce NUMA affinity
    topology_manager_policy_numa = ['best-effort', 'restricted', 'single-numa-node']
    if topo_mgr_policy in topology_manager_policy_numa:
        validate_equals(
            len(procs), 1,
            f"Pod {podname} container cpuset spans a single processor.")

    # Validate CPUs are allocated in HT sibling pairs where possible
    isolcpu_keywords.validate_ht_sibling_pairs(
        worker_ssh_connection, podname, host_cpu_output)


def _verify_pod_resources_and_assignment(
        ssh_connection: SSHConnection, host: str, topo_mgr_policy: str,
        podname: str, expected_isolcpus_allocated: int, expected_isolcpus_allocatable: int) -> None:
    """
    Verify pod resource accounting and CPU assignment.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        host (str): hostname of the worker node.
        topo_mgr_policy (str): topology manager policy (e.g. 'best-effort', 'single-numa-node').
        podname (str): name of the pod to verify.
        expected_isolcpus_allocated (int): expected allocated isolcpus after pod starts.
        expected_isolcpus_allocatable (int): expected allocatable isolcpus (unchanged).
    """
    _verify_isolcpu_resource_accounting(
        ssh_connection, host, expected_isolcpus_allocatable, expected_isolcpus_allocated)
    _verify_pod_cpu_assignment(ssh_connection, host, podname, topo_mgr_policy)


def _deploy_and_verify_pending_pod(
        ssh_connection: SSHConnection, podname: str, filename: str) -> None:
    """
    Deploy an isolcpu pod that is expected to fail scheduling due to exhausted resources.

    The pod may land in Pending, TopologyAffinityError, or UnexpectedAdmissionError state
    depending on the topology manager policy and resource exhaustion scenario.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        podname (str): name of the pod to create.
        filename (str): path to the rendered YAML file on the remote host.
    """
    logger = get_logger()
    logger.log_test_case_step(f"Create pod {podname} expecting failure due to exhausted isolcpus")
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(filename)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
        pod_name=podname,
        expected_status=["Pending", "TopologyAffinityError", "UnexpectedAdmissionError"],
        timeout=360)


def _delete_pod_to_free_resources(ssh_connection: SSHConnection, pod_to_delete: str, created_pods: list) -> None:
    """
    Delete a running pod to free isolcpu resources.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        pod_to_delete (str): name of the running pod to delete.
        created_pods (list): mutable list of tracked pod names; pod_to_delete is removed.
    """
    logger = get_logger()
    logger.log_test_case_step(f"Delete pod {pod_to_delete} to free isolcpu resources")
    KubectlDeletePodsKeywords(ssh_connection).delete_pod(pod_to_delete)
    created_pods.remove(pod_to_delete)


def _verify_recovered_pod_resources(
        ssh_connection: SSHConnection, host: str, topo_mgr_policy: str,
        podname: str, expected_isolcpus: tuple) -> None:
    """
    Verify recovered pod resource accounting and CPU assignment.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        host (str): hostname of the worker node.
        topo_mgr_policy (str): topology manager policy (e.g. 'best-effort', 'single-numa-node').
        podname (str): name of the recovered pod to verify.
        expected_isolcpus (tuple): (expected_allocatable, expected_allocated) isolcpu counts after recovery.
    """
    _verify_isolcpu_resource_accounting(ssh_connection, host, expected_isolcpus[0], expected_isolcpus[1])
    _verify_pod_cpu_assignment(ssh_connection, host, podname, topo_mgr_policy)


@mark.p2
@mark.lab_has_hyperthreading
def test_isolcpu_exhaust_and_recover_none_policy(request):
    """
    Test validates isolcpu exhaustion and Pending pod recovery with 'none' topology policy.

    This test validates the recovery behavior for pods in Pending state with 'none' topology
    manager policy. When resources are exhausted, pods enter Pending state and automatically
    transition to Running once resources become available (without requiring manual deletion/recreation).

    Args:
        request: pytest request object used to register the teardown finalizer.

    Test Steps:
        - Configure 'none' topology manager policy
        - Check isolcpu_plugin is active on the worker host
        - Check cpu-manager-policy=static
        - Validate at least 3 allocatable Application-isolated CPUs available on processor 0
        - Create pods with 3 and 2 isolated-cpu until there is no more cpu resources on the host
        - Verify the pods are in Running state and requested cpus are allocated
        - Verify the allocated cpu are in pairs if possible
        - Create a new pod requesting 2 cpus
        - Verify the new pod is in Pending state
        - Delete one of the Running pod
        - Verify the Pending pod goes to Running state
        - Verify the two requested cpus are allocated to the new pod
        - Verify the allocated cpu are in pairs if possible

    Teardown:
        - Delete all created pod YAML files and pods
        - Restore original isolated cores configuration if modified
    """
    pod_name_prefix = "isolcpu-exhaust-recover-none"

    logger = get_logger()
    logger.log_setup_step("Get active controller SSH connection")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    logger.log_setup_step("Get worker host with allocatable isolcpus")
    host = _get_worker_host(ssh_connection, request)

    logger.log_setup_step(f"Get worker SSH connection for {host}")
    worker_ssh_connection = LabConnectionKeywords().get_ssh_for_hostname(host)

    # Configure 'none' topology manager policy
    _configure_topology_manager_policy(ssh_connection, host, "none")
    expected_policy = "none"

    logger.log_setup_step(f"Check isolcpu_plugin is active on {host}")
    IsolcpuKeywords(ssh_connection).validate_isolcpu_plugin_active(worker_ssh_connection, host)

    logger.log_setup_step(f"Check cpu-manager-policy=static on {host}")
    ProcessStatusArgsKeywords(worker_ssh_connection).validate_kubelet_cpu_manager_policy(host, "static")

    logger.log_setup_step(f"Get allocatable isolcpus on {host}")
    allocatable_isolcpus = KubectlDescribeNodeKeywords(ssh_connection).describe_node(host)\
        .get_node_description().get_allocatable().get_windriver_isolcpus()
    logger.log_info(f"Allocatable isolcpus on {host}: {allocatable_isolcpus}")

    logger.log_setup_step(f"Get CPU topology on {host}")
    host_cpu_output = SystemHostCPUKeywords(ssh_connection).get_system_host_cpu_list(host)

    logger.log_setup_step(f"Get number of Application-isolated logical cores on processor 0 on {host}")
    req_isol_p0 = host_cpu_output.get_number_of_logical_cores(
        processor_id=0, assigned_function='Application-isolated'
    )

    validate_greater_than_or_equal(
        req_isol_p0, 3,
        f"Application-isolated logical cores on processor 0 on {host}: expected at least 3, observed {req_isol_p0}")
    validate_greater_than_or_equal(
        allocatable_isolcpus, 3,
        f"Allocatable isolcpus on {host}: expected at least 3, observed {allocatable_isolcpus}")

    created_files = []
    created_pods = []

    def teardown():
        logger.log_teardown_step("Delete created pods and YAML files")
        for pod in created_pods:
            KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(pod)
        for filepath in created_files:
            FileKeywords(ssh_connection).delete_file(filepath)
        FileKeywords(ssh_connection).delete_directory("/home/sysadmin/isolcpus/test_files/")

    request.addfinalizer(teardown)

    pod_to_delete = None
    requested_isocpu = 3
    pod_number = 1
    expected_isolcpus_allocated = 0
    expected_isolcpus_allocatable = allocatable_isolcpus

    # Exhaust isolcpu resources by creating pods with alternating CPU requests
    # Alternate between requesting 3 and 2 isolcpus per pod (XOR toggle: 3^1=2, 2^1=3)
    # until the remaining allocatable isolcpus are less than the next request.
    # The first pod created is tracked for deletion later to free resources.
    logger.log_test_case_step("Deploy pods to exhaust isolcpu resources")
    while allocatable_isolcpus >= requested_isocpu:
        # Generate unique pod name based on CPU request and sequence number
        podname = f"{pod_name_prefix}-{requested_isocpu}cpu-{pod_number}"

        # Create the pod YAML file from template with specified CPU request
        filename = _create_isolcpu_pod_yaml(ssh_connection, podname, requested_isocpu, host)
        created_files.append(filename)
        created_pods.append(podname)

        # Track the first pod to delete later to free isolcpu resources for recovery test
        if pod_number == 1:
            pod_to_delete = podname

        # Update expected allocated count before deploying pod
        expected_isolcpus_allocated += requested_isocpu

        # Deploy pod and verify it reaches Running state with correct resource allocation
        _deploy_isolcpu_pod(ssh_connection, podname, filename, requested_isocpu)
        _verify_pod_resources_and_assignment(
            ssh_connection, host, expected_policy,
            podname, expected_isolcpus_allocated, expected_isolcpus_allocatable)

        # Update remaining allocatable count and toggle CPU request for next pod (3 <-> 2)
        allocatable_isolcpus -= requested_isocpu
        requested_isocpu ^= 1  # XOR toggle between 3 and 2
        pod_number += 1

    # If the remaining isolcpus exactly match the next request, toggle to ensure
    # the next pod request exceeds available resources and enters Pending state
    if requested_isocpu == allocatable_isolcpus:
        requested_isocpu ^= 1

    # Create a pod that will fail to schedule due to insufficient resources
    # With 'none' topology policy, this pod will enter Pending state
    logger.log_test_case_step("Deploy pod that exceeds available isolcpu resources")
    podname = f"{pod_name_prefix}-{requested_isocpu}cpu-{pod_number + 1}"
    filename = _create_isolcpu_pod_yaml(ssh_connection, podname, requested_isocpu, host)
    created_files.append(filename)
    created_pods.append(podname)
    _deploy_and_verify_pending_pod(ssh_connection, podname, filename)

    # Verify pod is in Pending state (expected behavior with 'none' topology policy)
    # Note: In some cases, UnexpectedAdmissionError may also occur with 'none' policy
    pod_status = KubectlGetPodsKeywords(ssh_connection).get_pods().get_pod(podname).get_status()
    if pod_status not in ["Pending", "UnexpectedAdmissionError"]:
        fail(f"Expected Pending or UnexpectedAdmissionError state with 'none' topology policy but pod is in {pod_status} state")
    logger.log_info(f"Pod {podname} is in {pod_status} state with topology policy: {expected_policy}")

    # Delete a running pod to free resources and trigger recovery
    _delete_pod_to_free_resources(ssh_connection, pod_to_delete, created_pods)

    # Handle recovery based on pod state
    if pod_status == "Pending":
        # With 'none' topology policy, Pending pods automatically transition to Running
        # once resources become available (no manual deletion/recreation required)
        logger.log_test_case_step(f"Pod {podname} is in Pending state, waiting for it to transition to Running")
        KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
            pod_name=podname, expected_status="Running", timeout=360)
    elif pod_status == "UnexpectedAdmissionError":
        # Error state pods need to be deleted and recreated
        logger.log_test_case_step(f"Pod {podname} is in UnexpectedAdmissionError state, deleting and recreating")
        KubectlDeletePodsKeywords(ssh_connection).delete_pod(podname)
        KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(filename)
        KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
            pod_name=podname, expected_status="Running", timeout=360)

    # Verify the recovered pod has correct resource allocation and CPU assignment
    _verify_recovered_pod_resources(
        ssh_connection, host, expected_policy, podname,
        (expected_isolcpus_allocatable, expected_isolcpus_allocated - 3 + requested_isocpu))


@mark.p2
@mark.lab_has_hyperthreading
def test_isolcpu_exhaust_and_recover_best_effort_policy(request):
    """
    Test validates isolcpu exhaustion and Pending pod recovery with 'best-effort' topology policy.

    This test validates the recovery behavior for pods in Pending state with 'best-effort' topology
    manager policy. When resources are exhausted, pods enter Pending state and automatically
    transition to Running once resources become available (without requiring manual deletion/recreation).

    Args:
        request: pytest request object used to register the teardown finalizer.

    Test Steps:
        - Configure 'best-effort' topology manager policy
        - Check isolcpu_plugin is active on the worker host
        - Check cpu-manager-policy=static
        - Validate at least 3 allocatable Application-isolated CPUs available on processor 0
        - Create pods with 3 and 2 isolated-cpu until there is no more cpu resources on the host
        - Verify the pods are in Running state and requested cpus are allocated
        - Verify the allocated cpu are in pairs if possible
        - Create a new pod requesting 2 cpus
        - Verify the new pod is in Pending state
        - Delete one of the Running pod
        - Verify the Pending pod goes to Running state
        - Verify the two requested cpus are allocated to the new pod
        - Verify the allocated cpu are in pairs if possible

    Teardown:
        - Delete all created pod YAML files and pods
        - Restore original isolated cores configuration if modified
    """
    pod_name_prefix = "isolcpu-exhaust-recover-best-effort"

    logger = get_logger()
    logger.log_setup_step("Get active controller SSH connection")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    logger.log_setup_step("Get worker host with allocatable isolcpus")
    host = _get_worker_host(ssh_connection, request)

    logger.log_setup_step(f"Get worker SSH connection for {host}")
    worker_ssh_connection = LabConnectionKeywords().get_ssh_for_hostname(host)

    # Configure 'best-effort' topology manager policy
    _configure_topology_manager_policy(ssh_connection, host, "best-effort")
    expected_policy = "best-effort"

    logger.log_setup_step(f"Check isolcpu_plugin is active on {host}")
    IsolcpuKeywords(ssh_connection).validate_isolcpu_plugin_active(worker_ssh_connection, host)

    logger.log_setup_step(f"Check cpu-manager-policy=static on {host}")
    ProcessStatusArgsKeywords(worker_ssh_connection).validate_kubelet_cpu_manager_policy(host, "static")

    logger.log_setup_step(f"Get allocatable isolcpus on {host}")
    allocatable_isolcpus = KubectlDescribeNodeKeywords(ssh_connection).describe_node(host)\
        .get_node_description().get_allocatable().get_windriver_isolcpus()
    logger.log_info(f"Allocatable isolcpus on {host}: {allocatable_isolcpus}")

    logger.log_setup_step(f"Get CPU topology on {host}")
    host_cpu_output = SystemHostCPUKeywords(ssh_connection).get_system_host_cpu_list(host)

    logger.log_setup_step(f"Get number of Application-isolated logical cores on processor 0 on {host}")
    req_isol_p0 = host_cpu_output.get_number_of_logical_cores(
        processor_id=0, assigned_function='Application-isolated'
    )

    validate_greater_than_or_equal(
        req_isol_p0, 3,
        f"Application-isolated logical cores on processor 0 on {host}: expected at least 3, observed {req_isol_p0}")
    validate_greater_than_or_equal(
        allocatable_isolcpus, 3,
        f"Allocatable isolcpus on {host}: expected at least 3, observed {allocatable_isolcpus}")

    created_files = []
    created_pods = []

    def teardown():
        logger.log_teardown_step("Delete created pods and YAML files")
        for pod in created_pods:
            KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(pod)
        for filepath in created_files:
            FileKeywords(ssh_connection).delete_file(filepath)
        FileKeywords(ssh_connection).delete_directory("/home/sysadmin/isolcpus/test_files/")

    request.addfinalizer(teardown)

    pod_to_delete = None
    requested_isocpu = 3
    pod_number = 1
    expected_isolcpus_allocated = 0
    expected_isolcpus_allocatable = allocatable_isolcpus

    # Exhaust isolcpu resources by creating pods with alternating CPU requests
    # Alternate between requesting 3 and 2 isolcpus per pod (XOR toggle: 3^1=2, 2^1=3)
    # until the remaining allocatable isolcpus are less than the next request.
    # The first pod created is tracked for deletion later to free resources.
    logger.log_test_case_step("Deploy pods to exhaust isolcpu resources")
    while allocatable_isolcpus >= requested_isocpu:
        # Generate unique pod name based on CPU request and sequence number
        podname = f"{pod_name_prefix}-{requested_isocpu}cpu-{pod_number}"

        # Create the pod YAML file from template with specified CPU request
        filename = _create_isolcpu_pod_yaml(ssh_connection, podname, requested_isocpu, host)
        created_files.append(filename)
        created_pods.append(podname)

        # Track the first pod to delete later to free isolcpu resources for recovery test
        if pod_number == 1:
            pod_to_delete = podname

        # Update expected allocated count before deploying pod
        expected_isolcpus_allocated += requested_isocpu

        # Deploy pod and verify it reaches Running state with correct resource allocation
        _deploy_isolcpu_pod(ssh_connection, podname, filename, requested_isocpu)
        _verify_pod_resources_and_assignment(
            ssh_connection, host, expected_policy,
            podname, expected_isolcpus_allocated, expected_isolcpus_allocatable)

        # Update remaining allocatable count and toggle CPU request for next pod (3 <-> 2)
        allocatable_isolcpus -= requested_isocpu
        requested_isocpu ^= 1  # XOR toggle between 3 and 2
        pod_number += 1

    # If the remaining isolcpus exactly match the next request, toggle to ensure
    # the next pod request exceeds available resources and enters Pending state
    if requested_isocpu == allocatable_isolcpus:
        requested_isocpu ^= 1

    # Create a pod that will fail to schedule due to insufficient resources
    # With 'best-effort' topology policy, this pod will enter Pending state
    logger.log_test_case_step("Deploy pod that exceeds available isolcpu resources")
    podname = f"{pod_name_prefix}-{requested_isocpu}cpu-{pod_number + 1}"
    filename = _create_isolcpu_pod_yaml(ssh_connection, podname, requested_isocpu, host)
    created_files.append(filename)
    created_pods.append(podname)
    _deploy_and_verify_pending_pod(ssh_connection, podname, filename)

    # Verify pod is in Pending state (expected behavior with 'best-effort' topology policy)
    # Note: In some cases, UnexpectedAdmissionError may also occur with 'best-effort' policy
    pod_status = KubectlGetPodsKeywords(ssh_connection).get_pods().get_pod(podname).get_status()
    if pod_status not in ["Pending", "UnexpectedAdmissionError"]:
        fail(f"Expected Pending or UnexpectedAdmissionError state with 'best-effort' topology policy but pod is in {pod_status} state")
    logger.log_info(f"Pod {podname} is in {pod_status} state with topology policy: {expected_policy}")

    # Delete a running pod to free resources and trigger recovery
    _delete_pod_to_free_resources(ssh_connection, pod_to_delete, created_pods)

    # Handle recovery based on pod state
    if pod_status == "Pending":
        # With 'best-effort' topology policy, Pending pods automatically transition to Running
        # once resources become available (no manual deletion/recreation required)
        logger.log_test_case_step(f"Pod {podname} is in Pending state, waiting for it to transition to Running")
        KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
            pod_name=podname, expected_status="Running", timeout=360)
    elif pod_status == "UnexpectedAdmissionError":
        # Error state pods need to be deleted and recreated
        logger.log_test_case_step(f"Pod {podname} is in UnexpectedAdmissionError state, deleting and recreating")
        KubectlDeletePodsKeywords(ssh_connection).delete_pod(podname)
        KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(filename)
        KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
            pod_name=podname, expected_status="Running", timeout=360)

    # Verify the recovered pod has correct resource allocation and CPU assignment
    _verify_recovered_pod_resources(
        ssh_connection, host, expected_policy, podname,
        (expected_isolcpus_allocatable, expected_isolcpus_allocated - 3 + requested_isocpu))


@mark.p2
@mark.lab_has_hyperthreading
def test_isolcpu_topology_affinity_error_recovery(request):
    """
    Test validates TopologyAffinityError recovery when NUMA resources are exhausted
    with single-numa-node topology policy.

    This test validates the recovery behavior for pods in TopologyAffinityError state.
    When NUMA resources are exhausted with single-numa-node policy, pods enter
    TopologyAffinityError state and must be manually deleted and recreated to recover
    (they do not automatically retry scheduling).

    Args:
        request: pytest request object used to register the teardown finalizer.

    Test Steps:
        - Verify worker has single-numa-node topology policy (fail if not)
        - Exhaust isolcpu resources on a single NUMA node
        - Create pod that triggers TopologyAffinityError
        - Verify pod is in TopologyAffinityError state
        - Delete a running pod to free resources
        - Verify errored pod is deleted and recreated to reach Running state

    Teardown:
        - Delete all created pod YAML files and pods
    """

    pod_name_prefix = "isolcpu-topo-affinity-error"
    logger = get_logger()

    # Step 1: Get SSH connections
    logger.log_setup_step("Get active controller SSH connection")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    logger.log_setup_step("Get worker host with allocatable isolcpus")
    host = _get_worker_host(ssh_connection, request)

    logger.log_setup_step(f"Get worker SSH connection for {host}")
    worker_ssh_connection = LabConnectionKeywords().get_ssh_for_hostname(host)

    # Configure 'single-numa-node' topology manager policy (required for TopologyAffinityError)
    _configure_topology_manager_policy(ssh_connection, host, "single-numa-node")

    # Step 3: Verify prerequisites
    logger.log_setup_step(f"Check isolcpu_plugin is active on {host}")
    IsolcpuKeywords(ssh_connection).validate_isolcpu_plugin_active(worker_ssh_connection, host)

    logger.log_setup_step(f"Get allocatable isolcpus on {host}")
    allocatable_isolcpus = KubectlDescribeNodeKeywords(ssh_connection).describe_node(host)\
        .get_node_description().get_allocatable().get_windriver_isolcpus()

    # Need at least 3 isolcpus to run the test
    validate_greater_than_or_equal(
        allocatable_isolcpus, 3,
        f"Allocatable isolcpus on {host}: expected at least 3, observed {allocatable_isolcpus}")

    created_files = []
    created_pods = []

    def teardown():
        logger.log_teardown_step("Delete created pods and YAML files")
        for pod in created_pods:
            KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(pod)
        for filepath in created_files:
            FileKeywords(ssh_connection).delete_file(filepath)
        FileKeywords(ssh_connection).delete_directory("/home/sysadmin/isolcpus/test_files/")

    request.addfinalizer(teardown)

    # Step 4: Exhaust isolcpu resources to trigger TopologyAffinityError
    # With single-numa-node policy, when NUMA resources are exhausted,
    # new pods will enter TopologyAffinityError state instead of Pending
    logger.log_test_case_step("Deploy pods to exhaust isolcpu resources")
    pod_number = 1
    requested_isocpu = 3
    expected_isolcpus_allocated = 0
    expected_isolcpus_allocatable = allocatable_isolcpus
    pod_to_delete = None

    # Create pods until resources are exhausted
    while allocatable_isolcpus >= requested_isocpu:
        podname = f"{pod_name_prefix}-{requested_isocpu}cpu-{pod_number}"
        filename = _create_isolcpu_pod_yaml(ssh_connection, podname, requested_isocpu, host)
        created_files.append(filename)
        created_pods.append(podname)

        # Track first pod for deletion later to free resources
        if pod_number == 1:
            pod_to_delete = podname

        expected_isolcpus_allocated += requested_isocpu
        _deploy_isolcpu_pod(ssh_connection, podname, filename, requested_isocpu)
        _verify_pod_resources_and_assignment(
            ssh_connection, host, "single-numa-node",
            podname, expected_isolcpus_allocated, expected_isolcpus_allocatable)

        allocatable_isolcpus -= requested_isocpu
        requested_isocpu ^= 1  # Toggle between 3 and 2
        pod_number += 1

    # Ensure next request exceeds available resources
    if requested_isocpu == allocatable_isolcpus:
        requested_isocpu ^= 1

    # Step 5: Create pod that triggers TopologyAffinityError
    # This pod cannot be scheduled because:
    # 1. Resources are exhausted
    # 2. single-numa-node policy requires all resources on one NUMA node
    # 3. Kubernetes marks it as TopologyAffinityError instead of Pending
    logger.log_test_case_step("Deploy pod expecting TopologyAffinityError")
    podname = f"{pod_name_prefix}-error-{pod_number}"
    filename = _create_isolcpu_pod_yaml(ssh_connection, podname, requested_isocpu, host)
    created_files.append(filename)
    created_pods.append(podname)
    _deploy_and_verify_pending_pod(ssh_connection, podname, filename)

    # Step 6: Verify pod is in TopologyAffinityError state
    # TopologyAffinityError occurs with single-numa-node topology policy when NUMA resources are exhausted
    pod_status = KubectlGetPodsKeywords(ssh_connection).get_pods().get_pod(podname).get_status()
    if pod_status != "TopologyAffinityError":
        fail(f"Test expects TopologyAffinityError state but pod is in {pod_status}. "
             f"This test requires single-numa-node topology policy.")
    logger.log_info(f"Pod {podname} is in {pod_status} state")

    # Step 7: Free resources and verify recovery
    # TopologyAffinityError pods must be deleted and recreated to recover
    logger.log_test_case_step("Free resources and verify TopologyAffinityError pod recovers")
    _delete_pod_to_free_resources(ssh_connection, pod_to_delete, created_pods)

    # Delete the errored pod
    logger.log_test_case_step(f"Pod {podname} is in TopologyAffinityError state, deleting and recreating")
    KubectlDeletePodsKeywords(ssh_connection).delete_pod(podname)

    # Recreate the pod from YAML to retry scheduling
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(filename)

    # Wait for pod to reach Running state
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
        pod_name=podname, expected_status="Running", timeout=360)
    _verify_recovered_pod_resources(
        ssh_connection, host, "single-numa-node", podname,
        (expected_isolcpus_allocatable, expected_isolcpus_allocated - 3 + requested_isocpu))


@mark.p2
@mark.lab_has_hyperthreading
def test_isolcpu_unexpected_admission_error_recovery(request):
    """
    Test validates error recovery with restricted topology policy.

    This test validates the recovery behavior for pods in error state with restricted policy.
    When resources are exhausted with restricted topology policy, pods enter an error state
    (UnexpectedAdmissionError or TopologyAffinityError depending on Kubernetes version)
    and must be manually deleted and recreated to recover (they do not automatically retry scheduling).

    Args:
        request: pytest request object used to register the teardown finalizer.

    Test Steps:
        - Verify worker has restricted topology policy (configure if not)
        - Exhaust isolcpu resources
        - Create pod that triggers error state
        - Verify pod is in error state (UnexpectedAdmissionError or TopologyAffinityError)
        - Delete a running pod to free resources
        - Verify errored pod is deleted and recreated to reach Running state

    Teardown:
        - Delete all created pod YAML files and pods
    """

    pod_name_prefix = "isolcpu-admission-error"
    logger = get_logger()

    # Step 1: Get SSH connections
    logger.log_setup_step("Get active controller SSH connection")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    logger.log_setup_step("Get worker host with allocatable isolcpus")
    host = _get_worker_host(ssh_connection, request)

    logger.log_setup_step(f"Get worker SSH connection for {host}")
    worker_ssh_connection = LabConnectionKeywords().get_ssh_for_hostname(host)

    # Configure 'restricted' topology manager policy (required for UnexpectedAdmissionError)
    _configure_topology_manager_policy(ssh_connection, host, "restricted")

    # Step 3: Verify prerequisites
    logger.log_setup_step(f"Check isolcpu_plugin is active on {host}")
    IsolcpuKeywords(ssh_connection).validate_isolcpu_plugin_active(worker_ssh_connection, host)

    logger.log_setup_step(f"Get allocatable isolcpus on {host}")
    allocatable_isolcpus = KubectlDescribeNodeKeywords(ssh_connection).describe_node(host)\
        .get_node_description().get_allocatable().get_windriver_isolcpus()

    # Need at least 3 isolcpus to run the test
    validate_greater_than_or_equal(
        allocatable_isolcpus, 3,
        f"Allocatable isolcpus on {host}: expected at least 3, observed {allocatable_isolcpus}")

    created_files = []
    created_pods = []

    def teardown():
        logger.log_teardown_step("Delete created pods and YAML files")
        for pod in created_pods:
            KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(pod)
        for filepath in created_files:
            FileKeywords(ssh_connection).delete_file(filepath)
        FileKeywords(ssh_connection).delete_directory("/home/sysadmin/isolcpus/test_files/")

    request.addfinalizer(teardown)

    # Step 4: Exhaust isolcpu resources to trigger UnexpectedAdmissionError
    # With restricted policy, when resources are exhausted and topology constraints
    # cannot be satisfied, new pods will enter UnexpectedAdmissionError state
    logger.log_test_case_step("Deploy pods to exhaust isolcpu resources")
    pod_number = 1
    requested_isocpu = 3
    expected_isolcpus_allocated = 0
    expected_isolcpus_allocatable = allocatable_isolcpus
    pod_to_delete = None

    # Create pods until resources are exhausted
    while allocatable_isolcpus >= requested_isocpu:
        podname = f"{pod_name_prefix}-{requested_isocpu}cpu-{pod_number}"
        filename = _create_isolcpu_pod_yaml(ssh_connection, podname, requested_isocpu, host)
        created_files.append(filename)
        created_pods.append(podname)

        # Track first pod for deletion later to free resources
        if pod_number == 1:
            pod_to_delete = podname

        expected_isolcpus_allocated += requested_isocpu
        _deploy_isolcpu_pod(ssh_connection, podname, filename, requested_isocpu)
        _verify_pod_resources_and_assignment(
            ssh_connection, host, "restricted",
            podname, expected_isolcpus_allocated, expected_isolcpus_allocatable)

        allocatable_isolcpus -= requested_isocpu
        requested_isocpu ^= 1  # Toggle between 3 and 2
        pod_number += 1

    # Ensure next request exceeds available resources
    if requested_isocpu == allocatable_isolcpus:
        requested_isocpu ^= 1

    # Step 5: Create pod that triggers UnexpectedAdmissionError
    # This pod cannot be scheduled because:
    # 1. Resources are exhausted
    # 2. restricted policy enforces strict topology constraints
    # 3. Kubernetes marks it as UnexpectedAdmissionError instead of Pending
    logger.log_test_case_step("Deploy pod expecting UnexpectedAdmissionError")
    podname = f"{pod_name_prefix}-error-{pod_number}"
    filename = _create_isolcpu_pod_yaml(ssh_connection, podname, requested_isocpu, host)
    created_files.append(filename)
    created_pods.append(podname)
    _deploy_and_verify_pending_pod(ssh_connection, podname, filename)

    # Step 6: Verify pod is in error state
    # With restricted topology policy, when resources are exhausted and topology constraints
    # cannot be satisfied, the pod enters an error state. The specific error state depends on
    # the Kubernetes version: UnexpectedAdmissionError or TopologyAffinityError.
    # Both indicate the same condition and require the same recovery action (delete/recreate).
    pod_status = KubectlGetPodsKeywords(ssh_connection).get_pods().get_pod(podname).get_status()
    if pod_status not in ["UnexpectedAdmissionError", "TopologyAffinityError"]:
        fail(f"Test expects UnexpectedAdmissionError or TopologyAffinityError state but pod is in {pod_status}. "
             f"This test requires restricted topology policy.")
    logger.log_info(f"Pod {podname} is in {pod_status} state with restricted topology policy")

    # Step 7: Free resources and verify recovery
    # Error state pods (UnexpectedAdmissionError or TopologyAffinityError) must be deleted and recreated to recover
    logger.log_test_case_step(f"Free resources and verify {pod_status} pod recovers")
    _delete_pod_to_free_resources(ssh_connection, pod_to_delete, created_pods)

    # Delete the errored pod
    logger.log_test_case_step(f"Pod {podname} is in {pod_status} state, deleting and recreating")
    KubectlDeletePodsKeywords(ssh_connection).delete_pod(podname)

    # Recreate the pod from YAML to retry scheduling
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(filename)

    # Wait for pod to reach Running state
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
        pod_name=podname, expected_status="Running", timeout=360)
    _verify_recovered_pod_resources(
        ssh_connection, host, "restricted", podname,
        (expected_isolcpus_allocatable, expected_isolcpus_allocated - 3 + requested_isocpu))
