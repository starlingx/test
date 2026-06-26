"""Output class for kubectl get crd command."""

from keywords.k8s.crd.object.kubectl_crd_object import KubectlCrdObject
from keywords.k8s.crd.object.kubectl_get_crd_table_parser import KubectlGetCrdTableParser


class KubectlGetCrdOutput:
    """Class to parse and query CRD list output."""

    def __init__(self, kubectl_get_crd_output: str | list[str]):
        """Initialize CRD output.

        Args:
            kubectl_get_crd_output (str | list[str]): Raw output from kubectl get crd.
        """
        self.crds: list[KubectlCrdObject] = []
        parser = KubectlGetCrdTableParser(kubectl_get_crd_output)
        output_values_list = parser.get_output_values_list()

        for crd_dict in output_values_list:
            if "NAME" not in crd_dict:
                continue
            crd = KubectlCrdObject(crd_dict["NAME"])
            if "CREATED AT" in crd_dict:
                crd.set_created_at(crd_dict["CREATED AT"])
            self.crds.append(crd)

    def get_crd_names(self) -> list[str]:
        """Get all CRD names.

        Returns:
            list[str]: List of CRD names.
        """
        return [crd.get_name() for crd in self.crds]

    def crd_exists(self, crd_name: str) -> bool:
        """Check if a CRD with the given name is registered.

        Args:
            crd_name (str): Full CRD name.

        Returns:
            bool: True if CRD exists, False otherwise.
        """
        return crd_name in self.get_crd_names()
