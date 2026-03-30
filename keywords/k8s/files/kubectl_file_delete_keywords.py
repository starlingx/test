from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlFileDeleteKeywords(K8sBaseKeyword):
    """
    Keywords for delete file resources
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def delete_resources(self, file_path: str, ignore_not_found: bool = False, validate: bool = True) -> str:
        """Delete Kubernetes resources defined in the given file.

        Args:
            file_path (str): The file path.
            ignore_not_found (bool): Whether to ignore not found errors.
            validate (bool): Enable validation. Defaults to True.

        Returns:
            str: The output.
        """
        cmd = f"kubectl delete -f {file_path}"

        if not validate:
            cmd += " --validate=false"

        if ignore_not_found:
            cmd += " --ignore-not-found=true"

        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

        return output
