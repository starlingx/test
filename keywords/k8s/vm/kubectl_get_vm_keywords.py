from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetVmKeywords(K8sBaseKeyword):
    """Keywords for kubectl get vm operations."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Initialize the KubectlGetVmKeywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_vm_status(self, vm_name: str, namespace: str = "default") -> str:
        """Get VM printable status using kubectl.

        Args:
            vm_name (str): Name of the VM.
            namespace (str): Namespace of the VM. Defaults to 'default'.

        Returns:
            str: VM status string.
        """
        cmd = f"kubectl get vm {vm_name} -n {namespace} -o jsonpath='{{.status.printableStatus}}'"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return output[0] if output else ""

    def wait_for_vm_status(self, vm_name: str, expected_status: str = "Running", namespace: str = "default", timeout: int = 60, poll_interval: int = 5) -> None:
        """Wait for VM to reach expected status.

        Args:
            vm_name (str): Name of the VM.
            expected_status (str): Expected VM status. Defaults to 'Running'.
            namespace (str): Namespace of the VM. Defaults to 'default'.
            timeout (int): Maximum time to wait in seconds. Defaults to 60.
            poll_interval (int): Time between checks in seconds. Defaults to 5.

        Raises:
            TimeoutError: If VM doesn't reach expected status within timeout.
        """
        # Polls VM printableStatus until it matches the expected status.
        # Fails fast if VM enters an error state.
        validate_equals_with_retry(
            function_to_execute=lambda: self.get_vm_status(vm_name, namespace),
            expected_value=expected_status,
            validation_description=f"VM {vm_name} to reach status {expected_status}",
            timeout=timeout,
            polling_sleep_time=poll_interval,
            failure_values=["ErrorUnschedulable", "CrashLoopBackOff", "ErrImagePull"],
        )
