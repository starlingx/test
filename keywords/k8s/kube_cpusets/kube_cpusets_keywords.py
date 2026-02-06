from typing import List

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_list_contains
from keywords.base_keyword import BaseKeyword
from keywords.k8s.kube_cpusets.object.kube_cpusets_output import KubeCpusetsOutput


class KubeCpusetsKeywords(BaseKeyword):
    """Keywords for kube-cpusets operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize KubeCpusetsKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        self.ssh_connection = ssh_connection

    def get_kube_cpusets_output(self) -> KubeCpusetsOutput:
        """Execute kube-cpusets command and return parsed output.

        Executes the kube-cpusets command via SSH to retrieve container CPU assignments
        and parses the output into structured objects.

        Returns:
            KubeCpusetsOutput: Parsed output containing all container CPU assignments.

        Raises:
            KeywordException: If command execution fails.
        """
        output = self.ssh_connection.send_as_sudo("kube-cpusets")
        self.validate_success_return_code(self.ssh_connection)

        # send_as_sudo returns a list, convert to string
        if isinstance(output, list):
            output = "".join(output)

        return KubeCpusetsOutput(output)

    def verify_pods_running_on_specific_cores(self, pod_names: List[str], cores: List[int]) -> None:
        """Verify that specified pods are running on specific CPU cores.

        Args:
            pod_names (List[str]): List of pod name patterns to verify (e.g., ['kmm-operator']).
            cores (List[int]): List of CPU core IDs to validate against.

        Raises:
            ValueError: If no containers found or using cores not in the specified list.
        """
        get_logger().log_info(f"Verifying pods {pod_names} are running on cores {cores}")

        cpusets_output = self.get_kube_cpusets_output()

        # Collect containers matching any of the pod name patterns
        containers = []
        for pod_name in pod_names:
            containers.extend(cpusets_output.get_containers_by_pod_name(pod_name))

        get_logger().log_debug(f"Found {len(containers)} containers for pods {pod_names}")
        # Verify each container is using specified cores
        for container in containers:
            get_logger().log_debug(f"Checking container {container.get_pod_name()}: " f"group={container.get_group()}, cpus={container.get_cpus()}")

            # Verify all container CPUs are in the specified cores list
            container_cpus = container.get_cpu_list()
            get_logger().log_debug(f"Container {container.get_pod_name()} CPU list: {container_cpus}")

            for cpu in container_cpus:
                validate_list_contains(cpu, cores, f"{container.get_pod_name()} CPU {cpu} is in specified cores")

        get_logger().log_info(f"All containers for pods {pod_names} are running on specified cores")
