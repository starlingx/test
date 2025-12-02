from typing import List

from keywords.k8s.helm.object.kubectl_get_helm_release_table_parser import KubectlGetHelmReleaseTableParser
from keywords.k8s.helm.object.kubectl_helm_release_object import KubectlHelmReleaseObject


class KubectlGetHelmReleaseOutput:
    """
    Class for 'kubectl get hr -A output' keywords
    """

    def __init__(self, kubectl_get_helm_release_output: str):
        """
        Constructor

        Args:
            kubectl_get_helm_release_output (str): Raw string output from running a "kubectl get hr -A" command.

        """
        self.kubectl_helm_release: [KubectlHelmReleaseObject] = []
        kubectl_get_helm_release_table_parser = KubectlGetHelmReleaseTableParser(kubectl_get_helm_release_output)
        output_values_list = kubectl_get_helm_release_table_parser.get_output_values_list()

        for helm_release_dict in output_values_list:

            if "NAME" not in helm_release_dict:
                raise ValueError(f"There is no NAME associated with the helm release: {helm_release_dict}")

            helm_release = KubectlHelmReleaseObject(helm_release_dict["NAME"])

            if "AGE" in helm_release_dict:
                helm_release.set_age(helm_release_dict["AGE"])

            if "READY" in helm_release_dict:
                helm_release.set_ready(helm_release_dict["READY"])

            if "STATUS" in helm_release_dict:
                helm_release.set_status(helm_release_dict["STATUS"])

            self.kubectl_helm_release.append(helm_release)

    def get_helm_releases(self) -> List[KubectlHelmReleaseObject]:
        """
        This function will get the list of all helm releases available.

        Returns: List of KubectlNamespaceObjects

        """
        return self.kubectl_helm_releases

    def is_helm_release(self, helm_release: str) -> bool:
        """
        This function will get the helm release with the name specified from this get_helm_release_output.

        Args:
            helm_release (str): The name of the helm release of interest.

        Returns:
            bool:  This function return a bool value.

        """
        for helm_release_name in self.kubectl_helm_release:
            if helm_release_name.get_name() == helm_release:
                return True
        else:
            return False
