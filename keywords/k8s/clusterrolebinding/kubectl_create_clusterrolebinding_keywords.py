from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlCreateClusterRoleBindingKeywords(K8sBaseKeyword):
    """Kubectl keywords for creating cluster role bindings."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def create_clusterrolebinding_for_group(self, binding_name: str, clusterrole: str, group: str) -> None:
        """Create a cluster role binding for a group.

        Args:
            binding_name (str): Name of the cluster role binding.
            clusterrole (str): Name of the cluster role to bind.
            group (str): Group to bind the role to (e.g. '/wrcp-admin').
        """
        cmd = f"kubectl create clusterrolebinding {binding_name} --clusterrole={clusterrole} --group={group}"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info(f"ClusterRoleBinding '{binding_name}' created: {clusterrole} -> group {group}")

    def delete_clusterrolebinding(self, binding_name: str) -> None:
        """Delete a cluster role binding.

        Args:
            binding_name (str): Name of the cluster role binding to delete.
        """
        cmd = f"kubectl delete clusterrolebinding {binding_name} --ignore-not-found"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info(f"ClusterRoleBinding '{binding_name}' deleted.")
