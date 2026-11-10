"""Kubernetes resource identity."""

import copy


class KubernetesResourceObject:
    """Encapsulate a checked Kubernetes resource."""

    def __init__(self, resource: dict):
        """Capture a resource.

        Args:
            resource (dict): Kubernetes resource payload.
        """
        self.resource = copy.deepcopy(resource)

    def get_name(self) -> str:
        """Return resource name.

        Returns:
            str: Name.
        """
        return self.resource["metadata"]["name"]

    def get_label(self, name: str) -> str | None:
        """Return a label, preserving absence.

        Args:
            name (str): Label key.

        Returns:
            str | None: Label value or absence.
        """
        return self.resource["metadata"].get("labels", {}).get(name)
