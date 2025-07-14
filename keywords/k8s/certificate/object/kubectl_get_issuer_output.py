from keywords.k8s.certificate.object.kubectl_get_issuer_table_parser import KubectlGetIssuerTableParser
from keywords.k8s.certificate.object.kubectl_issuer_object import KubectlIssuerObject


class KubectlGetIssuerOutput:
    """
    This class represents the output of the 'kubectl get issuer' command.

    It provides methods to parse and retrieve issuer information from the command output.
    """

    def __init__(self, kubectl_get_issuer_output: str):
        """
        Constructor

        Args:
            kubectl_get_issuer_output (str): Raw string output from running a "kubectl get issuer" command.

        """
        self.kubectl_issuer: [KubectlIssuerObject] = []
        kubectl_get_issuer_table_parser = KubectlGetIssuerTableParser(kubectl_get_issuer_output)
        output_values_list = kubectl_get_issuer_table_parser.get_output_values_list()

        for pod_dict in output_values_list:

            if "NAME" not in pod_dict:
                raise ValueError(f"There is no NAME associated with the issuer: {pod_dict}")

            issuer = KubectlIssuerObject(pod_dict["NAME"])

            if "READY" in pod_dict:
                issuer.set_ready(pod_dict["READY"])

            if "AGE" in pod_dict:
                issuer.set_age(pod_dict["AGE"])

            self.kubectl_issuer.append(issuer)

    def get_issuer(self, issuer_name: str) -> KubectlIssuerObject:
        """
        This function will get the pod with the name specified from this get_issuer_output.

        Args:
            issuer_name (str): The name of the issuer.

        Returns:
            KubectlIssuerObject: The issuer object with the specified name.

        Raises:
            ValueError: If no issuer with the specified name is found.

        """
        for issuer in self.kubectl_issuer:
            if issuer.get_name() == issuer_name:
                return issuer
        else:
            raise ValueError(f"There is no issuer with the name {issuer_name}.")
