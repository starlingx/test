from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlCreatePodsKeywords(BaseKeyword):
    """
    Class for Kubectl Create pod keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def create_from_yaml(self, yaml_file: str):
        """
        Creates a pod from yaml file
        Args:
            yaml_file (): the yaml file

        Returns:

        """
        self.ssh_connection.send(export_k8s_config(f"kubectl create -f {yaml_file}"))
        self.validate_success_return_code(self.ssh_connection)
