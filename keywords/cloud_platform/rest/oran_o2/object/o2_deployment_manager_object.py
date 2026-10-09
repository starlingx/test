from typing import Optional


class O2DeploymentManagerObject:
    """Represents a single O2 IMS deployment manager."""

    def __init__(self, deployment_manager_id: str):
        """Constructor.

        Args:
            deployment_manager_id (str): The deploymentManagerId value.
        """
        self.deployment_manager_id = deployment_manager_id
        self.supported_locations = None
        self.capabilities = None
        self.capacity = None
        self.extensions_present = False

    def get_deployment_manager_id(self) -> str:
        """Get the deployment manager id.

        Returns:
            str: The deploymentManagerId value.
        """
        return self.deployment_manager_id

    def set_supported_locations(self, supported_locations: Optional[str]) -> None:
        """Set supportedLocations.

        Args:
            supported_locations (Optional[str]): The supportedLocations value, or None if absent.
        """
        self.supported_locations = supported_locations

    def get_supported_locations(self) -> Optional[str]:
        """Get supportedLocations.

        Returns:
            Optional[str]: The supportedLocations value, or None if the key was absent.
        """
        return self.supported_locations

    def set_capabilities(self, capabilities: Optional[dict]) -> None:
        """Set capabilities.

        Args:
            capabilities (Optional[dict]): The capabilities value, or None if absent.
        """
        self.capabilities = capabilities

    def get_capabilities(self) -> Optional[dict]:
        """Get capabilities.

        Returns:
            Optional[dict]: The capabilities value, or None if the key was absent.
        """
        return self.capabilities

    def set_capacity(self, capacity: Optional[dict]) -> None:
        """Set capacity.

        Args:
            capacity (Optional[dict]): The capacity value, or None if absent.
        """
        self.capacity = capacity

    def get_capacity(self) -> Optional[dict]:
        """Get capacity.

        Returns:
            Optional[dict]: The capacity value, or None if the key was absent.
        """
        return self.capacity

    def set_extensions_present(self, extensions_present: bool) -> None:
        """Set whether the entry carried an extensions key.

        Args:
            extensions_present (bool): True if the payload carried the key.
        """
        self.extensions_present = extensions_present

    def has_extensions(self) -> bool:
        """Return whether the entry carried an extensions key.

        Presence is tracked rather than the value because a list read returns the
        key with a null value, so the value cannot distinguish a field-expanded
        read from a plain one while the presence of the key can.

        Returns:
            bool: True if the payload carried an extensions key.
        """
        return self.extensions_present
