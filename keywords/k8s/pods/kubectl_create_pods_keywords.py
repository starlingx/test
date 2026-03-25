from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlCreatePodsKeywords(K8sBaseKeyword):
    """
    Class for Kubectl Create pod keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): the ssh connection
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def create_from_yaml(self, yaml_file: str) -> None:
        """
        Creates a pod from yaml file

        Args:
            yaml_file (str): the yaml file
        """
        self.ssh_connection.send(self.k8s_config.export(f"kubectl create -f {yaml_file}"))
        self.validate_success_return_code(self.ssh_connection)
