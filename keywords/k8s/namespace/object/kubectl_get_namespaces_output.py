from typing import List

from keywords.k8s.namespace.object.kubectl_get_namespaces_table_parser import KubectlGetNamespacesTableParser
from keywords.k8s.namespace.object.kubectl_namespace_object import KubectlNamespaceObject


class KubectlGetNamespacesOutput:

    def __init__(self, kubectl_get_namespaces_output: str):
        """
        Constructor

        Args:
            kubectl_get_namespaces_output: Raw string output from running a "kubectl get ns" command.

        """

        self.kubectl_namespaces: [KubectlNamespaceObject] = []
        kubectl_get_namespaces_table_parser = KubectlGetNamespacesTableParser(kubectl_get_namespaces_output)
        output_values_list = kubectl_get_namespaces_table_parser.get_output_values_list()

        for namespace_dict in output_values_list:

            if 'NAME' not in namespace_dict:
                raise ValueError(f"There is no NAME associated with the namespace: {namespace_dict}")

            namespace = KubectlNamespaceObject(namespace_dict['NAME'])

            if 'STATUS' in namespace_dict:
                namespace.set_status(namespace_dict['STATUS'])

            if 'AGE' in namespace_dict:
                namespace.set_age(namespace_dict['AGE'])

            self.kubectl_namespaces.append(namespace)

    def get_namespaces(self) -> List[KubectlNamespaceObject]:
        """
        This function will get the list of all namespaces available.

        Returns: List of KubectlNamespaceObjects

        """
        return self.kubectl_namespaces
