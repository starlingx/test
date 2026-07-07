"""Object representing a Kubernetes ConfigMap."""

from typing import Optional


class KubectlConfigmapObject:
    """Represents a single Kubernetes ConfigMap resource."""

    def __init__(self) -> None:
        """Initialize an empty ConfigMap object."""
        self.name: str = ""
        self.namespace: str = ""
        self.data: dict = {}

    def get_name(self) -> str:
        """Get the ConfigMap name.

        Returns:
            str: The name of the ConfigMap.
        """
        return self.name

    def set_name(self, name: str) -> None:
        """Set the ConfigMap name.

        Args:
            name (str): The name of the ConfigMap.
        """
        self.name = name

    def get_namespace(self) -> str:
        """Get the ConfigMap namespace.

        Returns:
            str: The namespace of the ConfigMap.
        """
        return self.namespace

    def set_namespace(self, namespace: str) -> None:
        """Set the ConfigMap namespace.

        Args:
            namespace (str): The namespace of the ConfigMap.
        """
        self.namespace = namespace

    def get_data(self) -> dict:
        """Get the full data dictionary of the ConfigMap.

        Returns:
            dict: All key-value pairs in the ConfigMap data section.
        """
        return self.data

    def set_data(self, data: dict) -> None:
        """Set the full data dictionary of the ConfigMap.

        Args:
            data (dict): The data dictionary to set.
        """
        self.data = data

    def get_data_value(self, key: str) -> Optional[str]:
        """Get a specific value from the ConfigMap data by key.

        Args:
            key (str): The data key to look up.

        Returns:
            Optional[str]: The value for the key, or None if not found.
        """
        return self.data.get(key)

    def has_data_key(self, key: str) -> bool:
        """Check if a specific key exists in the ConfigMap data.

        Args:
            key (str): The data key to check.

        Returns:
            bool: True if the key exists in data.
        """
        return key in self.data

    def __str__(self) -> str:
        """Return string representation of the ConfigMap.

        Returns:
            str: Human-readable representation.
        """
        return f"ConfigMap(name={self.name}, namespace={self.namespace}, keys={list(self.data.keys())})"
