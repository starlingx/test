from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlApplyPodsKeywords(K8sBaseKeyword):
    """
    Class for Kubectl apply pod keywords

    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): ssh connection
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.

        """
        super().__init__(ssh_connection, kubeconfig_path)

    def apply_from_yaml(self, yaml_file: str, namespace: str = None) -> None:
        """
        Applies a pod yaml config

        Args:
            yaml_file (str): the yaml file
            namespace (str, optional): the namespace to apply the yaml to
        Returns: None

        """
        ns_arg = f"-n {namespace}" if namespace else ""
        self.ssh_connection.send(self.k8s_config.export(f"kubectl apply -f {yaml_file} {ns_arg}"))
        self.validate_success_return_code(self.ssh_connection)

    def fail_apply_from_yaml(self, yaml_file: str) -> None:
        """
        Checks if applying a pod yaml config fails

        Args:
            yaml_file (str): the yaml file

        Returns:
            None:  This function does not return a value.

        """
        self.ssh_connection.send(self.k8s_config.export(f"kubectl apply -f {yaml_file}"))
        rc = self.ssh_connection.get_return_code()
        if 1 != rc:
            raise Exception(f"Expected deployment of {yaml_file} to fail, instead it passed, investigate")
