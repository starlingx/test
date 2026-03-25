from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlDeleteDaemonsetAppsKeywords(K8sBaseKeyword):
    """
    Class for kubctl daemonset.apps keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        super().__init__(ssh_connection, kubeconfig_path)

    def delete_daemonset_apps(self, daemonset_app_name: str) -> None:
        """Delete the given daemonset.apps.

        Args:
            daemonset_app_name (str): The name of the daemonset.app.
        """
        self.ssh_connection.send(self.k8s_config.export(f"kubectl delete daemonset.apps {daemonset_app_name}"))
        self.validate_success_return_code(self.ssh_connection)

    def cleanup_daemonset_apps(self, daemonset_apps_name: str) -> int:
        """Clean up the given daemonset.app without failing on non-zero return code.

        Args:
            daemonset_apps_name (str): The name of the daemonset app.

        Returns:
            int: The return code of the delete command.
        """
        self.ssh_connection.send(self.k8s_config.export(f"kubectl delete daemonset.apps {daemonset_apps_name}"))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"Pod {daemonset_apps_name} failed to delete")
        return rc
