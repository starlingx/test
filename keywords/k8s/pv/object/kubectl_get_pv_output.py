"""Output parser for kubectl get pv command."""

from typing import List, Union

from framework.exceptions.keyword_exception import KeywordException
from keywords.k8s.pv.object.kubectl_get_pv_table_parser import KubectlGetPvTableParser
from keywords.k8s.pv.object.kubectl_pv_object import KubectlPvObject


class KubectlGetPvOutput:
    """Parses and provides access to kubectl get pv output."""

    def __init__(self, kubectl_get_pv_output: Union[str, List[str]]):
        """Constructor.

        Args:
            kubectl_get_pv_output (Union[str, List[str]]): Raw output from kubectl get pv.
        """
        self.pvs: List[KubectlPvObject] = []
        table_parser = KubectlGetPvTableParser(kubectl_get_pv_output)
        output_values_list = table_parser.get_output_values_list()

        for pv_dict in output_values_list:
            if "NAME" not in pv_dict:
                raise KeywordException(f"No NAME in PV output: {pv_dict}")

            pv = KubectlPvObject(pv_dict["NAME"])

            if "CAPACITY" in pv_dict:
                pv.set_capacity(pv_dict["CAPACITY"])
            if "ACCESS MODES" in pv_dict:
                pv.set_access_modes(pv_dict["ACCESS MODES"])
            if "RECLAIM POLICY" in pv_dict:
                pv.set_reclaim_policy(pv_dict["RECLAIM POLICY"])
            if "STATUS" in pv_dict:
                pv.set_status(pv_dict["STATUS"])
            if "CLAIM" in pv_dict:
                pv.set_claim(pv_dict["CLAIM"])
            if "STORAGECLASS" in pv_dict:
                pv.set_storageclass(pv_dict["STORAGECLASS"])
            if "REASON" in pv_dict:
                pv.set_reason(pv_dict["REASON"])
            if "AGE" in pv_dict:
                pv.set_age(pv_dict["AGE"])
            if "VOLUMEMODE" in pv_dict:
                pv.set_volumemode(pv_dict["VOLUMEMODE"])

            self.pvs.append(pv)

    def get_pvs(self) -> List[KubectlPvObject]:
        """Get all PersistentVolumes.

        Returns:
            List[KubectlPvObject]: List of all PV objects.
        """
        return self.pvs

    def get_pv_by_name(self, name: str) -> KubectlPvObject:
        """Get a PV by name.

        Args:
            name (str): PV name.

        Returns:
            KubectlPvObject: The matching PV object.

        Raises:
            KeywordException: If no PV with the given name is found.
        """
        for pv in self.pvs:
            if pv.get_name() == name:
                return pv
        raise KeywordException(f"No PV with name '{name}' found.")

    def get_bound_pvs(self) -> List[KubectlPvObject]:
        """Get all PVs with Bound status.

        Returns:
            List[KubectlPvObject]: List of bound PV objects.
        """
        return [pv for pv in self.pvs if pv.is_bound()]

    def get_pvs_by_claim_namespace(self, namespace: str) -> List[KubectlPvObject]:
        """Get PVs whose claim belongs to a specific namespace.

        Args:
            namespace (str): The namespace to filter by (e.g., 'monitor').

        Returns:
            List[KubectlPvObject]: List of PV objects with claims in the given namespace.
        """
        return [pv for pv in self.pvs if pv.get_claim() and pv.get_claim().startswith(f"{namespace}/")]
