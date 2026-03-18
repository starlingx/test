from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_str_contains
from keywords.base_keyword import BaseKeyword


class ProcessStatusArgsKeywords(BaseKeyword):
    """
    Class for "ps -o args" keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller
        """
        self.ssh_connection = ssh_connection

    def get_process_arguments_as_string(self, process_name: str) -> str:
        """
        This function will return the command line arguments associated with the specified process.

        Args:
            process_name (str): The name of the process for which we want to get the command line arguments.

        Returns:
            str: A string containing the process name with all command line arguments.

        """
        output = self.ssh_connection.send(f"ps -C {process_name} -o args= | cat")
        self.validate_success_return_code(self.ssh_connection)

        # output is a list with one value
        output_string = output[0]
        return output_string

    def validate_kubelet_cpu_manager_policy(self, host: str, expected_cpu_manager_policy: str) -> None:
        """
        Validate that the kubelet process is running with the expected cpu-manager-policy.

        Args:
            host (str): hostname of the worker node, used in validation messages.
            expected_cpu_manager_policy (str): expected value for --cpu-manager-policy.

        Raises:
            Exception: if --cpu-manager-policy is not found in the kubelet process args.
        """
        kubelet_args = self.get_process_arguments_as_string("kubelet")
        validate_str_contains(
            kubelet_args, f"--cpu-manager-policy={expected_cpu_manager_policy}",
            f"kubelet --cpu-manager-policy on {host}: expected {expected_cpu_manager_policy}")

    def validate_kubelet_topology_manager_policy(self, host: str, expected_topology_manager_policy: str) -> None:
        """
        Validate that the kubelet process is running with the expected topology-manager-policy.

        Args:
            host (str): hostname of the worker node, used in validation messages.
            expected_topology_manager_policy (str): expected value for --topology-manager-policy.

        Raises:
            Exception: if --topology-manager-policy is not found in the kubelet process args.
        """
        kubelet_args = self.get_process_arguments_as_string("kubelet")
        validate_str_contains(
            kubelet_args, f"--topology-manager-policy={expected_topology_manager_policy}",
            f"kubelet --topology-manager-policy on {host}: expected {expected_topology_manager_policy}")
