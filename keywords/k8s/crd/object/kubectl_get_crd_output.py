"""Output class for kubectl get crd command."""

import json

from keywords.k8s.crd.object.kubectl_crd_object import KubectlCrdObject
from keywords.k8s.crd.object.kubectl_get_crd_table_parser import KubectlGetCrdTableParser


class KubectlGetCrdOutput:
    """Class to parse and query CRD list output."""

    def __init__(self, kubectl_get_crd_output: str | list[str], source: str = "table"):
        """Initialize CRD output.

        Args:
            kubectl_get_crd_output (str | list[str]): Raw output from kubectl get crd.
            source (str): Source format of the output. 'table' for default kubectl output,
                'json' for -o json output.
        """
        self.crds: list[KubectlCrdObject] = []

        if source == "json":
            self._parse_json(kubectl_get_crd_output)
        else:
            self._parse_table(kubectl_get_crd_output)

    def _parse_table(self, kubectl_get_crd_output: str | list[str]) -> None:
        """Parse table-format output from kubectl get crd.

        Args:
            kubectl_get_crd_output (str | list[str]): Raw table output.
        """
        parser = KubectlGetCrdTableParser(kubectl_get_crd_output)
        output_values_list = parser.get_output_values_list()

        for crd_dict in output_values_list:
            if "NAME" not in crd_dict:
                continue
            crd = KubectlCrdObject(crd_dict["NAME"])
            if "CREATED AT" in crd_dict:
                crd.set_created_at(crd_dict["CREATED AT"])
            self.crds.append(crd)

    def _parse_json(self, kubectl_get_crd_output: str | list[str]) -> None:
        """Parse JSON-format output from kubectl get crd -o json.

        Handles both single CRD and list of CRDs.

        Args:
            kubectl_get_crd_output (str | list[str]): Raw JSON output.
        """
        if isinstance(kubectl_get_crd_output, list):
            kubectl_get_crd_output = "".join(kubectl_get_crd_output)

        json_obj = json.loads(kubectl_get_crd_output)

        if json_obj.get("kind") == "CustomResourceDefinitionList":
            items = json_obj.get("items", [])
        else:
            items = [json_obj]

        for item in items:
            name = item.get("metadata", {}).get("name", "")
            if not name:
                continue
            crd = KubectlCrdObject(name)

            created_at = item.get("metadata", {}).get("creationTimestamp")
            if created_at:
                crd.set_created_at(created_at)

            conditions = item.get("status", {}).get("conditions", [])
            for condition in conditions:
                if condition.get("type") == "Established":
                    crd.set_established(condition.get("status") == "True")
                    break

            self.crds.append(crd)

    def get_crd_names(self) -> list[str]:
        """Get all CRD names.

        Returns:
            list[str]: List of CRD names.
        """
        return [crd.get_name() for crd in self.crds]

    def get_crd_by_name(self, crd_name: str) -> KubectlCrdObject:
        """Get a CRD object by name.

        Use is_crd_present() to check existence without raising.

        Args:
            crd_name (str): Full CRD name.

        Returns:
            KubectlCrdObject: The CRD object.

        Raises:
            ValueError: If no CRD with the given name is found.
        """
        for crd in self.crds:
            if crd.get_name() == crd_name:
                return crd
        raise ValueError(f"CRD '{crd_name}' not found in output")

    def is_crd_present(self, crd_name: str) -> bool:
        """Check if a CRD with the given name is registered.

        Args:
            crd_name (str): Full CRD name.

        Returns:
            bool: True if CRD exists, False otherwise.
        """
        return crd_name in self.get_crd_names()

    def get_crds_by_group(self, group: str) -> list[KubectlCrdObject]:
        """Get CRDs filtered by API group.

        Args:
            group (str): API group to filter by (e.g. 'monitoring.coreos.com').

        Returns:
            list[KubectlCrdObject]: CRDs matching the group.
        """
        return [crd for crd in self.crds if crd.get_group() == group]

    def get_crd_names_by_group(self, group: str) -> list[str]:
        """Get CRD names filtered by API group.

        Args:
            group (str): API group to filter by.

        Returns:
            list[str]: CRD names matching the group.
        """
        return [crd.get_name() for crd in self.get_crds_by_group(group)]
