"""Keywords for bulk-deleting Helm-related Kubernetes CRD resources.

This module provides bulk deletion (--all) of Helm CRD resources within a
namespace. It complements KubectlDeleteHelmReleaseKeywords (which deletes a
single HelmRelease by name) by supporting namespace-wide teardown scenarios
such as application uninstall or orphaned resource cleanup.

Relationship to existing keywords:
    - KubectlDeleteHelmReleaseKeywords: Targeted deletion of a single
      HelmRelease by name (kubectl delete hr <name> -n <ns>).
    - KubectlDeleteAllHelmResourcesKeywords (this class): Bulk deletion of
      all HelmReleases, HelmCharts, and HelmRepositories in a namespace
      (kubectl delete <resource> --all -n <ns>). Used for namespace teardown.
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlDeleteAllHelmResourcesKeywords(BaseKeyword):
    """Keywords for bulk-deleting all Helm CRD resources in a namespace.

    Supports deletion of HelmReleases, HelmCharts, and HelmRepositories
    using --all --ignore-not-found=true for idempotent teardown operations.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize with SSH connection.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.
        """
        self.ssh_connection = ssh_connection

    def delete_all_helm_releases(self, namespace: str) -> None:
        """Delete all HelmReleases in a namespace.

        Args:
            namespace (str): Target namespace.
        """
        get_logger().log_info(f"Deleting all HelmReleases in namespace {namespace}")
        self.ssh_connection.send(export_k8s_config(f"kubectl delete helmrelease --all -n {namespace} --ignore-not-found=true"))
        self.validate_success_return_code(self.ssh_connection)

    def delete_all_helm_charts(self, namespace: str) -> None:
        """Delete all HelmCharts in a namespace.

        Args:
            namespace (str): Target namespace.
        """
        get_logger().log_info(f"Deleting all HelmCharts in namespace {namespace}")
        self.ssh_connection.send(export_k8s_config(f"kubectl delete helmchart --all -n {namespace} --ignore-not-found=true"))
        self.validate_success_return_code(self.ssh_connection)

    def delete_all_helm_repositories(self, namespace: str) -> None:
        """Delete all HelmRepositories in a namespace.

        Args:
            namespace (str): Target namespace.
        """
        get_logger().log_info(f"Deleting all HelmRepositories in namespace {namespace}")
        self.ssh_connection.send(export_k8s_config(f"kubectl delete helmrepository --all -n {namespace} --ignore-not-found=true"))
        self.validate_success_return_code(self.ssh_connection)

    def delete_all_helm_resources(self, namespace: str) -> None:
        """Delete all Helm CRD resources (releases, charts, repositories) in a namespace.

        Args:
            namespace (str): Target namespace.
        """
        self.delete_all_helm_releases(namespace)
        self.delete_all_helm_charts(namespace)
        self.delete_all_helm_repositories(namespace)
