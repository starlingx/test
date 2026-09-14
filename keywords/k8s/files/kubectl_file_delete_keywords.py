from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.files.file_keywords import FileKeywords
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
        # 'kubectl delete -f' fails with a non-zero return code when the manifest file
        # itself is missing. '--ignore-not-found' only ignores absent Kubernetes
        # resources, not an absent '-f' file. When the caller asked to ignore
        # not-found, treat a missing manifest file as nothing-to-delete.
        if ignore_not_found and not FileKeywords(self.ssh_connection).file_exists(file_path):
            get_logger().log_info(f"Manifest file {file_path} does not exist, skipping delete (ignore_not_found=True).")
            return ""

        cmd = f"kubectl delete -f {file_path}"

        if not validate:
            cmd += " --validate=false"

        if ignore_not_found:
            cmd += " --ignore-not-found=true"

        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

        return output
