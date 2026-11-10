"""Typed resource list JSON parser."""

import json

from keywords.k8s.get_resource.object.kubernetes_resource_object import KubernetesResourceObject


class KubernetesResourceListOutput:
    """Decode resource identities from checked JSON."""

    def __init__(self, content: str):
        """Parse a list response.

        Args:
            content (str): Kubernetes list JSON.
        """
        self.resources = [KubernetesResourceObject(item) for item in json.loads(content)["items"]]

    def get_resources(self) -> list[KubernetesResourceObject]:
        """Return resource identity objects.

        Returns:
            list[KubernetesResourceObject]: Resource records.
        """
        return list(self.resources)

    def find_resource(self, name: str) -> KubernetesResourceObject | None:
        """Find a resource without treating confirmed absence as a read failure.

        Args:
            name (str): Resource name.

        Returns:
            KubernetesResourceObject | None: Matching resource or absence.
        """
        return next((resource for resource in self.resources if resource.get_name() == name), None)

    def get_labels(self, label: str) -> dict[str, str | None]:
        """Return each resource's value for a selected label.

        Args:
            label (str): Label key.

        Returns:
            dict[str, str | None]: Names mapped to label values or absence.
        """
        return {resource.get_name(): resource.get_label(label) for resource in self.resources}
