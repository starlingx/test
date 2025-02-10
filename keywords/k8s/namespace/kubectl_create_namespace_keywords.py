from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlCreateNamespacesKeywords(BaseKeyword):
    """
    Class for 'kubectl create ns' keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def create_namespaces(self, name):
        """
        Create a k8s namespace
        Args:

        Returns: KubectlGetNamespacesOutput

        """
        self.ssh_connection.send(export_k8s_config(f"kubectl create ns {name}"))
        self.validate_success_return_code(self.ssh_connection)
