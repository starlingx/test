"""Deployment Manager CRD resource object."""

from typing import Optional

KUBECTL_EMPTY_VALUE = "<none>"


class KubectlDmResourceObject:
    """Represents one Deployment Manager CRD resource row from a 'kubectl get' table."""

    def __init__(self, name: str):
        """Constructor.

        Args:
            name (str): Name of the resource.
        """
        self.name = name
        self.type: Optional[str] = None
        self.insync: Optional[str] = None
        self.scope: Optional[str] = None
        self.reconciled: Optional[str] = None
        self.delta: Optional[str] = None
        self.description: Optional[str] = None

    def get_name(self) -> str:
        """Get the resource name.

        Returns:
            str: Resource name.
        """
        return self.name

    def set_type(self, resource_type: str) -> None:
        """Set the resource kind.

        Args:
            resource_type (str): Resource kind, e.g. "DataNetwork".
        """
        self.type = resource_type

    def get_type(self) -> Optional[str]:
        """Get the resource kind.

        Returns:
            Optional[str]: Resource kind.
        """
        return self.type

    def set_insync(self, insync: str) -> None:
        """Set the INSYNC value.

        Args:
            insync (str): INSYNC value, "true" or "false".
        """
        self.insync = insync

    def get_insync(self) -> Optional[str]:
        """Get the INSYNC value.

        Returns:
            Optional[str]: INSYNC value.
        """
        return self.insync

    def set_scope(self, scope: str) -> None:
        """Set the deployment scope.

        Args:
            scope (str): Deployment scope, e.g. "principal" or "bootstrap".
        """
        self.scope = scope

    def get_scope(self) -> Optional[str]:
        """Get the deployment scope.

        Returns:
            Optional[str]: Deployment scope.
        """
        return self.scope

    def set_reconciled(self, reconciled: str) -> None:
        """Set the RECONCILED value.

        Args:
            reconciled (str): RECONCILED value, "true" or "false".
        """
        self.reconciled = reconciled

    def get_reconciled(self) -> Optional[str]:
        """Get the RECONCILED value.

        Returns:
            Optional[str]: RECONCILED value.
        """
        return self.reconciled

    def set_delta(self, delta: str) -> None:
        """Set the configuration delta, normalising kubectl's '<none>' to an empty string.

        Args:
            delta (str): Raw delta column value.
        """
        self.delta = "" if delta == KUBECTL_EMPTY_VALUE else delta

    def get_delta(self) -> Optional[str]:
        """Get the configuration delta. Empty string means there is no delta.

        Returns:
            Optional[str]: Configuration delta.
        """
        return self.delta

    def set_description(self, description: str) -> None:
        """Set the description, normalising kubectl's '<none>' to an empty string.

        Args:
            description (str): Raw description column value.
        """
        self.description = "" if description == KUBECTL_EMPTY_VALUE else description

    def get_description(self) -> Optional[str]:
        """Get the resource description. Empty string means it is not set.

        Returns:
            Optional[str]: Resource description.
        """
        return self.description
