from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.globalnetworkpolicy.object.kubectl_get_globalnetworkpolicy_output import KubectlGetGlobalNetworkPolicyOutput
from keywords.k8s.globalnetworkpolicy.object.kubectl_globalnetworkpolicy_object import KubectlGlobalNetworkPolicyObject
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetGlobalNetworkPolicyKeywords(K8sBaseKeyword):
    """
    Class for 'kubectl get globalnetworkpolicies.crd.projectcalico.org' keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_globalnetworkpolicies(self) -> KubectlGetGlobalNetworkPolicyOutput:
        """Gets the Calico GlobalNetworkPolicies available.

        Returns:
            KubectlGetGlobalNetworkPolicyOutput: The GlobalNetworkPolicy output.
        """
        kubectl_get_globalnetworkpolicy_output = self.ssh_connection.send(self.k8s_config.export("kubectl get globalnetworkpolicies.crd.projectcalico.org"))
        self.validate_success_return_code(self.ssh_connection)
        globalnetworkpolicy_list_output = KubectlGetGlobalNetworkPolicyOutput(kubectl_get_globalnetworkpolicy_output)

        return globalnetworkpolicy_list_output

    def get_globalnetworkpolicy_by_name(self, policy_name: str) -> KubectlGlobalNetworkPolicyObject:
        """
        Gets a specific GlobalNetworkPolicy by name.

        Args:
            policy_name (str): The name of the GlobalNetworkPolicy to retrieve.

        Returns:
            KubectlGlobalNetworkPolicyObject: The GlobalNetworkPolicy object.

        Raises:
            ValueError: If the GlobalNetworkPolicy is not found.
        """
        globalnetworkpolicy_output = self.get_globalnetworkpolicies()
        return globalnetworkpolicy_output.get_globalnetworkpolicy_by_name(policy_name)

    def has_globalnetworkpolicy(self, policy_name: str) -> bool:
        """
        Check if GlobalNetworkPolicy exists.

        Returns False on any error, making it safe for polling validation.

        Args:
            policy_name (str): The name of the GlobalNetworkPolicy to check.

        Returns:
            bool: True if the policy exists, False otherwise.
        """
        try:
            globalnetworkpolicy_output = self.get_globalnetworkpolicies()
            return globalnetworkpolicy_output.has_globalnetworkpolicy(policy_name)
        except Exception:
            return False

    def get_globalnetworkpolicy_yaml(self, policy_name: str) -> str:
        """
        Get GlobalNetworkPolicy details in YAML format.

        Args:
            policy_name (str): The name of the GlobalNetworkPolicy to retrieve.

        Returns:
            str: The GlobalNetworkPolicy YAML as a string.

        Raises:
            Exception: If kubectl command fails or policy not found.
        """
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl get globalnetworkpolicy {policy_name} -o yaml"))
        self.validate_success_return_code(self.ssh_connection)
        return "\n".join(output) if isinstance(output, list) else output
