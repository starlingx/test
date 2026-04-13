from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlCreateClusterRoleKeywords(K8sBaseKeyword):
    """Kubectl keywords for creating and deleting cluster roles."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def create_clusterrole(self, role_name: str, verbs: list[str], resources: list[str]) -> None:
        """Create a cluster role with specified verbs and resources.

        Args:
            role_name (str): Name of the cluster role to create.
            verbs (list[str]): List of allowed verbs (e.g. ['get', 'list']).
            resources (list[str]): List of resources to apply the verbs to.
        """
        verbs_str = ",".join(verbs)
        resources_str = ",".join(resources)
        cmd = f"kubectl create clusterrole {role_name} --verb={verbs_str} --resource={resources_str}"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info(f"ClusterRole '{role_name}' created: verbs={verbs_str} resources={resources_str}")

    def delete_clusterrole(self, role_name: str) -> None:
        """Delete a cluster role.

        Args:
            role_name (str): Name of the cluster role to delete.
        """
        cmd = f"kubectl delete clusterrole {role_name} --ignore-not-found"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info(f"ClusterRole '{role_name}' deleted.")
