from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlDeleteResourceKeywords(K8sBaseKeyword):
    """
    Keywords for deleting generic Kubernetes resources by name.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def delete_resource(self, resource_type: str, resource_name: str, namespace: str = None) -> None:
        """Delete a Kubernetes resource by type and name. Does not fail the test on error.

        Args:
            resource_type (str): The resource type (e.g. "pod", "pvc",
                "volumesnapshots.snapshot.storage.k8s.io").
            resource_name (str): The resource name.
            namespace (str, optional): The namespace.
        """
        ns_arg = f"-n {namespace}" if namespace else ""
        cmd = f"kubectl delete {resource_type} {resource_name} {ns_arg} --ignore-not-found=true"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
