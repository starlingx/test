from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.sriov_vrb_node_config.object.kubectl_get_sriov_vrb_node_config_output import KubectlGetSriovVrbNodeConfigOutput


class KubectlGetSriovVrbNodeConfigKeywords(K8sBaseKeyword):
    """Class for 'kubectl get sriovvrbnodeconfigs.sriovvrb.intel.com' keywords."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_sriov_vrb_node_configs(self, namespace: str = "sriov-fec-system") -> KubectlGetSriovVrbNodeConfigOutput:
        """Get all SriovVrbNodeConfigs in the specified namespace.

        Args:
            namespace (str): Kubernetes namespace. Defaults to 'sriov-fec-system'.

        Returns:
            KubectlGetSriovVrbNodeConfigOutput: The SriovVrbNodeConfig output.
        """
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl get sriovvrbnodeconfigs.sriovvrb.intel.com -n {namespace}"))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetSriovVrbNodeConfigOutput(output)

    def wait_for_configured_status(self, node_name: str, expected_status: str = "Succeeded", namespace: str = "sriov-fec-system", timeout: int = 180, poll_interval: int = 10) -> None:
        """Wait for a SriovVrbNodeConfig to reach the expected CONFIGURED status.

        Args:
            node_name (str): The name of the node (e.g., 'controller-0').
            expected_status (str): Expected CONFIGURED status. Defaults to 'Succeeded'.
            namespace (str): Kubernetes namespace. Defaults to 'sriov-fec-system'.
            timeout (int): Maximum time in seconds to wait. Defaults to 180.
            poll_interval (int): Time in seconds between checks. Defaults to 10.

        Raises:
            TimeoutError: If the node does not reach the expected status within timeout.
        """

        def get_configured_status() -> str:
            config = self.get_sriov_vrb_node_configs(namespace).get_sriov_vrb_node_config_by_name(node_name)
            return config.get_configured()

        validate_equals_with_retry(
            function_to_execute=get_configured_status,
            expected_value=expected_status,
            validation_description=f"SriovVrbNodeConfig '{node_name}' CONFIGURED status is '{expected_status}'",
            timeout=timeout,
            polling_sleep_time=poll_interval,
        )
