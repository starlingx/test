from typing import Union

from framework.exceptions.keyword_exception import KeywordException
from keywords.k8s.pvc.object.kubectl_get_pvcs_table_parser import KubectlGetPvcsTableParser
from keywords.k8s.pvc.object.kubectl_pvc_object import KubectlPvcObject


class KubectlGetPvcsOutput:
    """A class to interact with and retrieve information about Kubernetes pvcs.

    This class provides methods to filter and retrieve pvc information
    using the kubectl command output.
    """

    def __init__(self, kubectl_get_pvcs_output: Union[str, list[str]]):
        """Constructor.

        Args:
            kubectl_get_pvcs_output (Union[str, list[str]]): Raw output from running a kubectl get pvc command.
        """
        self.kubectl_pvc: list[KubectlPvcObject] = []
        kubectl_get_pvcs_table_parser = KubectlGetPvcsTableParser(kubectl_get_pvcs_output)
        output_values_list = kubectl_get_pvcs_table_parser.get_output_values_list()

        for pvc_dict in output_values_list:

            if "NAME" not in pvc_dict:
                raise KeywordException(f"There is no NAME associated with the pvc: {pvc_dict}")

            pvc = KubectlPvcObject(pvc_dict["NAME"])

            if "NAMESPACE" in pvc_dict:
                pvc.set_namespace(pvc_dict["NAMESPACE"])

            if "STATUS" in pvc_dict:
                pvc.set_status(pvc_dict["STATUS"])

            if "VOLUME" in pvc_dict:
                pvc.set_volume(pvc_dict["VOLUME"])

            if "CAPACITY" in pvc_dict:
                pvc.set_capacity(pvc_dict["CAPACITY"])

            if "ACCESS MODES" in pvc_dict:
                pvc.set_access_modes(pvc_dict["ACCESS MODES"])

            if "STORAGECLASS" in pvc_dict:
                pvc.set_storageclass(pvc_dict["STORAGECLASS"])

            if "VOLUMEATTRIBUTESCLASS" in pvc_dict:
                pvc.set_volumeattributesclass(pvc_dict["VOLUMEATTRIBUTESCLASS"])

            if "AGE" in pvc_dict:
                pvc.set_age(pvc_dict["AGE"])

            if "VOLUMEMODE" in pvc_dict:
                pvc.set_volumemode(pvc_dict["VOLUMEMODE"])

            self.kubectl_pvc.append(pvc)

    def get_pvcs(self) -> list[KubectlPvcObject]:
        """Get all pvcs.

        Returns:
            list[KubectlPvcObject]: A list of all pvcs.
        """
        return self.kubectl_pvc
