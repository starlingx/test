from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlDeleteDaemonsetAppsKeywords(BaseKeyword):
    """
    Class for kubctl daemonset.apps keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def delete_daemonset_apps(self, daemonset_app_name):
        """
        Deletes the given daemonset.apps
        Args:
            daemonset_app_name (): the name of the daemonset.app

        Returns:

        """
        self.ssh_connection.send(export_k8s_config(f'kubectl delete daemonset.apps {daemonset_app_name}'))
        self.validate_success_return_code(self.ssh_connection)

    def cleanup_daemonset_apps(self, daemonset_apps_name):
        """
        Cleansup the given daemonset.app - should be used in teardown and won't fail/stop in case rc is non zero
        Args:
            daemonset_apps_name (): the name of the daemonset app

        Returns:

        """
        self.ssh_connection.send(export_k8s_config(f'kubectl delete daemonset.apps {daemonset_apps_name}'))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"Pod {daemonset_apps_name} failed to delete")
        return rc
