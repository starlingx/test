from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlCalicoctlApplyKeywords(BaseKeyword):
    """
    Class for Calicoctl apply kewords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def calicoctl_apply_from_yaml(self, yaml_file: str):
        """
        Does a calicoctl apply using the given yaml file
        Args:
            yaml_file (): the yaml file to appy

        Returns:

        """
        self.ssh_connection.send(export_k8s_config(f"kubectl calicoctl apply -f {yaml_file}"))
        self.validate_success_return_code(self.ssh_connection)