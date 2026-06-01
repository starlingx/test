"""Output wrapper for ``kubectl get ingress`` parsed rows."""

from typing import List

from keywords.k8s.ingress.object.kubectl_get_ingress_table_parser import KubectlGetIngressTableParser
from keywords.k8s.ingress.object.kubectl_ingress_object import KubectlIngressObject


class KubectlGetIngressOutput:
    """
    Class for output of the get ingress command.
    """

    def __init__(self, kubectl_get_ingress_output: list):
        """
        Constructor.

        Args:
            kubectl_get_ingress_output (list): Raw output from running a "kubectl get ingress" command.
        """
        self.kubectl_ingresses: List[KubectlIngressObject] = []
        parser = KubectlGetIngressTableParser(kubectl_get_ingress_output)
        output_values_list = parser.get_output_values_list()

        for ingress_dict in output_values_list:
            if "NAME" not in ingress_dict:
                continue
            ingress = KubectlIngressObject(ingress_dict["NAME"])
            if "CLASS" in ingress_dict:
                ingress.set_ingress_class(ingress_dict["CLASS"])
            if "HOSTS" in ingress_dict:
                ingress.set_hosts(ingress_dict["HOSTS"])
            if "ADDRESS" in ingress_dict:
                ingress.set_address(ingress_dict["ADDRESS"])
            if "PORTS" in ingress_dict:
                ingress.set_ports(ingress_dict["PORTS"])
            if "AGE" in ingress_dict:
                ingress.set_age(ingress_dict["AGE"])
            self.kubectl_ingresses.append(ingress)

    def get_ingresses(self) -> List[KubectlIngressObject]:
        """
        Get the list of all ingress resources parsed from the output.

        Returns:
            List[KubectlIngressObject]: List of parsed ingress objects.
        """
        return self.kubectl_ingresses

    def is_ingress(self, ingress_name: str) -> bool:
        """
        Check if an ingress with the given name is in this output.

        Args:
            ingress_name (str): The name of the ingress of interest.

        Returns:
            bool: True if an ingress with the given name is present, False otherwise.
        """
        for ingress in self.kubectl_ingresses:
            if ingress.get_name() == ingress_name:
                return True
        return False
