from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlDeleteImagePolicyKeywords(BaseKeyword):
    """Keywords for deleting Kubernetes image policies."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize kubectl delete image policy keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def delete_all_imagepolicies(self) -> None:
        """Delete all image policies in the cluster."""
        self.ssh_connection.send(export_k8s_config("kubectl delete imagepolicy --all --ignore-not-found=true"))
        self.validate_success_return_code(self.ssh_connection)

    def delete_all_clusterimagepolicies(self) -> None:
        """Delete all cluster image policies in the cluster."""
        self.ssh_connection.send(export_k8s_config("kubectl delete clusterimagepolicy --all --ignore-not-found=true"))
        self.validate_success_return_code(self.ssh_connection)
