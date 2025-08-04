from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlApplyPodsKeywords(BaseKeyword):
    """
    Class for Kubectl apply pod keywords

    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): ssh connection

        """
        self.ssh_connection = ssh_connection

    def apply_from_yaml(self, yaml_file: str, namespace: str = None) -> None:
        """
        Applies a pod yaml config

        Args:
            yaml_file (str): the yaml file
            namespace (str, optional): the namespace to apply the yaml to
        Returns: None

        """
        ns_arg = f"-n {namespace}" if namespace else ""
        self.ssh_connection.send(export_k8s_config(f"kubectl apply -f {yaml_file} {ns_arg}"))
        self.validate_success_return_code(self.ssh_connection)

    def fail_apply_from_yaml(self, yaml_file: str) -> None:
        """
        Checks if applying a pod yaml config fails

        Args:
            yaml_file (str): the yaml file

        Returns:
            None:  This function does not return a value.

        """
        self.ssh_connection.send(export_k8s_config(f"kubectl apply -f {yaml_file}"))
        rc = self.ssh_connection.get_return_code()
        if 1 != rc:
            raise Exception(f"Expected deployment of {yaml_file} to fail, instead it passed, investigate")
