from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.namespace.object.kubectl_get_namespaces_output import KubectlGetNamespacesOutput


class KubectlGetNamespacesKeywords(BaseKeyword):
    """
    Class for 'kubectl get ns' keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_namespaces(self) -> KubectlGetNamespacesOutput:
        """
        Gets the k8s namespaces available.
        Args:

        Returns: KubectlGetNamespacesOutput

        """
        kubectl_get_namespaces_output = self.ssh_connection.send(export_k8s_config("kubectl get ns"))
        self.validate_success_return_code(self.ssh_connection)
        namespaces_list_output = KubectlGetNamespacesOutput(kubectl_get_namespaces_output)

        return namespaces_list_output

    def get_namespaces_by_label(self, label) -> KubectlGetNamespacesOutput:
        """
        Gets the k8s namespaces available for a given label.
        Args:

        Returns: KubectlGetNamespacesOutput

        """
        kubectl_get_namespaces_output = self.ssh_connection.send(export_k8s_config(f"kubectl get ns -l={label}"))
        self.validate_success_return_code(self.ssh_connection)
        namespaces_list_output = KubectlGetNamespacesOutput(kubectl_get_namespaces_output)

        return namespaces_list_output
