"""Output parser for Deployment Manager CRD resources."""

import json

from framework.exceptions.keyword_exception import KeywordException
from keywords.k8s.crd.object.kubectl_dm_resources_object import KubectlDmResourceObject
from keywords.k8s.crd.object.kubectl_dm_resources_table_parser import KubectlDmResourcesTableParser


class KubectlDmResourcesOutput:
    """Parses the output of 'kubectl get <dm-resource> -n deployment', as a table or as JSON."""

    def __init__(self, kubectl_get_output: list[str], source: str = "table"):
        """Constructor.

        Args:
            kubectl_get_output (list[str]): Raw output lines of the 'kubectl get' command.
            source (str): "table" for the default printer columns, "json" for '-o json' output.

        Raises:
            KeywordException: If a row has no NAME value.
        """
        self.resources: list[KubectlDmResourceObject] = []

        if source == "json":
            self._parse_json(kubectl_get_output)
            return

        lines = [line for line in kubectl_get_output if line.strip()]
        if not lines or lines[0].startswith("No resources found"):
            return

        for row in KubectlDmResourcesTableParser(lines).get_output_values_list():
            if not row.get("NAME"):
                raise KeywordException(f"There is no NAME associated with the resource: {row}")

            resource = KubectlDmResourceObject(row["NAME"])
            if "TYPE" in row:
                resource.set_type(row["TYPE"])
            if "INSYNC" in row:
                resource.set_insync(row["INSYNC"])
            if "SCOPE" in row:
                resource.set_scope(row["SCOPE"])
            if "RECONCILED" in row:
                resource.set_reconciled(row["RECONCILED"])
            if "DELTA" in row:
                resource.set_delta(row["DELTA"])
            if "DESCRIPTION" in row:
                resource.set_description(row["DESCRIPTION"])
            self.resources.append(resource)

    def _parse_json(self, kubectl_get_output: list[str]) -> None:
        """Parse '-o json' output of a single resource or of a list of resources.

        Args:
            kubectl_get_output (list[str]): Raw output lines of the 'kubectl get -o json' command.
        """
        data = json.loads("".join(kubectl_get_output))
        items = data.get("items", []) if data.get("kind", "").endswith("List") else [data]
        for item in items:
            status = item.get("status", {})
            resource = KubectlDmResourceObject(item.get("metadata", {}).get("name"))
            resource.set_type(item.get("kind"))
            resource.set_description(item.get("spec", {}).get("description") or "")
            resource.set_scope(status.get("deploymentScope"))
            resource.set_reconciled(str(status.get("reconciled", "")).lower())
            resource.set_insync(str(status.get("inSync", "")).lower())
            resource.set_delta(status.get("delta") or "")
            self.resources.append(resource)

    def get_resources(self) -> list[KubectlDmResourceObject]:
        """Get all the parsed resources.

        Returns:
            list[KubectlDmResourceObject]: Parsed resources.
        """
        return self.resources

    def get_resource(self, name: str) -> KubectlDmResourceObject:
        """Get one resource by name.

        Args:
            name (str): Resource name.

        Returns:
            KubectlDmResourceObject: The matching resource.

        Raises:
            KeywordException: If no resource has that name.
        """
        for resource in self.resources:
            if resource.get_name() == name:
                return resource
        raise KeywordException(f"There is no resource with the name {name}.")
