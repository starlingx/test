from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetCronjobsKeywords(K8sBaseKeyword):
    """
    Keywords for getting Kubernetes cronjobs.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def is_cronjob_present(self, cronjob_name: str, namespace: str = None) -> bool:
        """Check whether a cronjob with the given name is present.

        Reads the cronjob's own name back via jsonpath. A missing cronjob
        yields an empty result (``--ignore-not-found``) rather than failing,
        and a present one echoes its exact name. An exact comparison is used
        rather than a substring test so a name that is a prefix of another
        cronjob (e.g. ``backup`` vs ``backup-weekly``) does not false-positive.

        Args:
            cronjob_name (str): The cronjob name.
            namespace (str): The namespace. Optional.

        Returns:
            bool: True if the cronjob is present.
        """
        cmd = f"kubectl get cronjob {cronjob_name} -o jsonpath='{{.metadata.name}}' --ignore-not-found"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        returned_name = ("\n".join(output) if isinstance(output, list) else str(output)).strip().strip("'")
        present = returned_name == cronjob_name
        get_logger().log_info(f"Cronjob '{cronjob_name}' present: {present}")
        return present
