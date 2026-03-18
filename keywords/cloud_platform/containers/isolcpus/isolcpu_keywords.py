"""
Keywords for isolated CPU pod validation and resource accounting operations.
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_str_contains
from keywords.base_keyword import BaseKeyword

from keywords.cloud_platform.system.host.objects.system_host_cpu_output import SystemHostCPUOutput
from keywords.k8s.cat.cat_cpu_manager_state_keywords import CatCpuManagerStateKeywords
from keywords.k8s.cat.cat_cpuset_keywords import CatCpuSetKeywords
from keywords.k8s.node.kubectl_describe_node_keywords import KubectlDescribeNodeKeywords
from keywords.linux.process_status.process_status_args_keywords import ProcessStatusArgsKeywords
from keywords.linux.systemctl.systemctl_is_active_keywords import SystemCTLIsActiveKeywords


class IsolcpuKeywords(BaseKeyword):
    """
    Keywords for isolated CPU pod validation operations.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initializes the IsolcpuKeywords class with an SSH connection to the active controller.

        Args:
            ssh_connection (SSHConnection): An instance of SSHConnection used for controller SSH operations.
        """
        self.ssh_connection = ssh_connection


    def validate_isolcpus_allocatable(self, host: str, expected_allocatable: int) -> None:
        """
        Validate that the allocatable isolcpus count matches the expected value.

        Allocatable is a static node property that only changes on reconfiguration,
        so it is read once without retry.

        Args:
            host (str): hostname of the node.
            expected_allocatable (int): expected total allocatable isolcpus on the node.

        Raises:
            Exception: if the allocatable count does not match.
        """
        get_logger().log_info(f"Checking {expected_allocatable} allocatable isolated cores on {host}")
        actual_allocatable = KubectlDescribeNodeKeywords(self.ssh_connection)\
            .describe_node(host).get_node_description()\
            .get_allocatable().get_windriver_isolcpus()
        validate_equals(
            actual_allocatable, expected_allocatable,
            f"Allocatable windriver.com/isolcpus on {host}: "
            f"expected {expected_allocatable}, observed {actual_allocatable}")


    def validate_isolcpus_allocated(
            self, host: str, expected_allocated: int,
            timeout: int = 120, check_interval: int = 10) -> None:
        """
        Validate that the allocated isolcpus count matches the expected value.

        Allocated count can lag briefly after pod scheduling, so it is retried
        until it converges to the expected value within the timeout.

        Args:
            host (str): hostname of the node.
            expected_allocated (int): expected number of allocated isolcpus.
            timeout (int): retry timeout in seconds.
            check_interval (int): retry interval in seconds.

        Raises:
            Exception: if the expected count is not met within timeout.
        """
        get_logger().log_info(f"Checking {expected_allocated} allocated isolated cores on {host}")

        def get_actual_allocated():
            allocated_resources = KubectlDescribeNodeKeywords(self.ssh_connection)\
                .describe_node(host).get_node_description().get_allocated_resources()
            windriver_isolcpus = allocated_resources.get_windriver_isolcpus()
            return 0 if windriver_isolcpus is None else windriver_isolcpus.get_requests_as_int()

        validate_equals_with_retry(
            get_actual_allocated,
            expected_allocated,
            f"Allocated windriver.com/isolcpus on {host}: expected {expected_allocated}",
            timeout=timeout,
            polling_sleep_time=check_interval)


    def get_pod_affinity_context(
            self, worker_ssh_connection: SSHConnection, podname: str,
            host_cpu_output: SystemHostCPUOutput) -> set:
        """
        Get processor IDs for CPUs assigned to a pod.

        Reads the cpu_manager_state file on the worker to find which logical CPUs were
        assigned to the pod's container, validates they are Application-isolated CPUs,
        and returns the set of processor IDs they belong to.

        Args:
            worker_ssh_connection (SSHConnection): SSH connection to the worker node.
            podname (str): name of the pod to check.
            host_cpu_output (SystemHostCPUOutput): parsed CPU list for the host, as
                returned by get_system_host_cpu_list(). Used to look up processor, physical
                core, thread, and function for each logical CPU ID.

        Returns:
            set: set of processor IDs that the assigned CPUs belong to.

        Raises:
            Exception: if cpuset is not a subset of Application-isolated CPUs.
        """
        logger = get_logger()

        isolcpus = host_cpu_output.get_log_cores_for_assigned_function('Application-isolated')

        logger.log_info(f"Reading cpuset path from pod {podname} to derive container name")
        contname = CatCpuSetKeywords(self.ssh_connection).get_cpuset_from_pod(podname)

        logger.log_info(f"Reading cpu_manager_state file for pod {podname}")
        state = CatCpuManagerStateKeywords(worker_ssh_connection)\
            .get_cpu_manager_state().get_cpu_manager_state_object()

        cpuset = set(state.get_container_cpuset(contname))

        validate_equals(
            cpuset.issubset(isolcpus), True,
            f"Pod {podname} container {contname} cpuset {cpuset} "
            f"is a subset of isolcpus {isolcpus}")

        procs = {
            host_cpu_output.get_system_host_cpu_from_log_core(cpu_id).get_processor()
            for cpu_id in cpuset
        }

        logger.log_info(f"Pod {podname} container {contname} cpuset {cpuset} spans processors {procs}")

        return procs


    def validate_isolcpu_plugin_active(self, worker_ssh_connection: SSHConnection, host: str) -> None:
        """
        Validate that the isolcpu_plugin service is active on the given host.

        Args:
            worker_ssh_connection (SSHConnection): SSH connection to the worker node.
            host (str): hostname of the node to check.

        Raises:
            Exception: if the isolcpu_plugin service is not active.
        """
        get_logger().log_info(f"Checking isolcpu_plugin service is active on {host}")
        status = SystemCTLIsActiveKeywords(worker_ssh_connection).is_active("isolcpu_plugin")
        validate_equals(status, "active", f"isolcpu_plugin service is active on {host}")


    def validate_ht_sibling_pairs(
            self, worker_ssh_connection: SSHConnection, podname: str,
            host_cpu_output: SystemHostCPUOutput) -> None:
        """
        Validate that CPUs are allocated in HT sibling pairs where possible.

        On a hyperthreaded host with static cpu-manager-policy, CPUs should be
        allocated in sibling pairs to maximise cache locality.
        Expected: floor(N/2)*2 paired CPUs and N%2 singletons for an N-CPU pod.

        Args:
            worker_ssh_connection (SSHConnection): SSH connection to the worker node.
            podname (str): name of the pod to check.
            host_cpu_output (SystemHostCPUOutput): parsed CPU list for the host.

        Example:
            For a 3-CPU pod on a hyperthreaded host:
            - Expected paired: 2 (one sibling pair)
            - Expected singletons: 1 (one unpaired CPU)

            For a 4-CPU pod on a hyperthreaded host:
            - Expected paired: 4 (two sibling pairs)
            - Expected singletons: 0 (all CPUs paired)

        Raises:
            Exception: if paired or singleton counts do not match expectations.
        """
        logger = get_logger()

        logger.log_info(f"Reading cpuset path from pod {podname} to derive container name")
        contname = CatCpuSetKeywords(self.ssh_connection).get_cpuset_from_pod(podname)

        logger.log_info(f"Reading cpu_manager_state file for pod {podname}")
        state = CatCpuManagerStateKeywords(worker_ssh_connection)\
            .get_cpu_manager_state().get_cpu_manager_state_object()

        cpuset = set(state.get_container_cpuset(contname))

        # Determine threads per core: 2 for hyperthreaded hosts, 1 otherwise
        threads_per_core = 2 if host_cpu_output.is_host_hyperthreaded() else 1

        # Count actual paired and singleton CPUs from the assigned cpuset
        paired = host_cpu_output.get_number_of_paired_cores(cpuset)
        singletons = host_cpu_output.get_number_of_singleton_cores(cpuset)

        # Calculate expected counts: N CPUs should yield floor(N/2)*2 paired and N%2 singletons
        expected_singletons = len(cpuset) % threads_per_core
        expected_paired = threads_per_core * int(len(cpuset) / threads_per_core)

        validate_equals(
            paired, expected_paired,
            f"Pod {podname} paired sibling count: expected {expected_paired}, observed {paired}")
        validate_equals(
            singletons, expected_singletons,
            f"Pod {podname} singleton count: expected {expected_singletons}, observed {singletons}")

