from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlCalicoctlApplyKeywords(K8sBaseKeyword):
    """
    Class for Calicoctl apply kewords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        super().__init__(ssh_connection, kubeconfig_path)

    def calicoctl_apply_from_yaml(self, yaml_file: str) -> None:
        """Apply a calicoctl resource using the given yaml file.

        Args:
            yaml_file (str): The yaml file to apply.
        """
        self.ssh_connection.send(self.k8s_config.export(f"kubectl calicoctl apply -f {yaml_file}"))
        self.validate_success_return_code(self.ssh_connection)
