"""Kubernetes PersistentVolumeClaim output parser."""

from typing import List, Union

from framework.exceptions.keyword_exception import KeywordException
from keywords.k8s.pvc.object.kubectl_get_pvcs_table_parser import KubectlGetPvcsTableParser
from keywords.k8s.pvc.object.kubectl_pvc_object import KubectlPvcObject


class KubectlGetPvcsOutput:
    """Parses and manages a collection of Kubernetes PVC resources.

    Parses table output from 'kubectl get pvc' and provides methods
    for querying PVCs by name, namespace, or StorageClass.
    """

    def __init__(self, kubectl_get_pvcs_output: Union[str, List[str]]) -> None:
        """Create PVC collection from kubectl table output.

        Args:
            kubectl_get_pvcs_output (Union[str, list[str]]): Raw output
                from 'kubectl get pvc'.
        """
        self.kubectl_pvc: List[KubectlPvcObject] = []
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

    def get_pvcs(self) -> List[KubectlPvcObject]:
        """Get all PVC objects.

        Returns:
            list[KubectlPvcObject]: List of all PVC objects.
        """
        return self.kubectl_pvc

    def get_pvc_by_name(self, name: str) -> KubectlPvcObject:
        """Get a PVC by exact name.

        Args:
            name (str): The name of the PVC.

        Returns:
            KubectlPvcObject: The matching PVC object.

        Raises:
            KeywordException: If no PVC with the given name exists.
        """
        for pvc in self.kubectl_pvc:
            if pvc.get_name() == name:
                return pvc
        raise KeywordException(f"No PVC with name '{name}' found.")

    def get_pvcs_by_namespace(self, namespace: str) -> List[KubectlPvcObject]:
        """Get PVCs filtered by namespace.

        Args:
            namespace (str): The namespace to filter by.

        Returns:
            list[KubectlPvcObject]: List of PVCs in the given namespace.
        """
        return [pvc for pvc in self.kubectl_pvc if pvc.get_namespace() == namespace]

    def get_pvcs_by_storageclass(self, storageclass_name: str) -> List[KubectlPvcObject]:
        """Get PVCs filtered by StorageClass.

        Args:
            storageclass_name (str): The StorageClass name to filter by.

        Returns:
            list[KubectlPvcObject]: List of PVCs using the given StorageClass.
        """
        return [pvc for pvc in self.kubectl_pvc if pvc.get_storageclass() == storageclass_name]

    def __str__(self) -> str:
        """Get string representation for logging.

        Returns:
            str: Human-readable summary of the PVC collection.
        """
        return f"KubectlGetPvcsOutput(count={len(self.kubectl_pvc)})"
