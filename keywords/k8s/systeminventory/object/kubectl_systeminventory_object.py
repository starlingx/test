from typing import Optional


class KubectlSystemInventoryObject:
    """
    Object class to hold SystemInventory resource attributes.
    """

    def __init__(self, name: str):
        """
        Constructor.

        Args:
            name (str): Name of the SystemInventory resource
        """
        self.name = name
        self.namespace = None
        self.status = None
        self.labels = {}

    def get_name(self) -> str:
        """
        Get the name of the SystemInventory resource.

        Returns:
            str: Resource name
        """
        return self.name

    def get_namespace(self) -> Optional[str]:
        """
        Get the namespace of the SystemInventory resource.

        Returns:
            Optional[str]: Namespace or None
        """
        return self.namespace

    def set_namespace(self, namespace: str) -> None:
        """
        Set the namespace.

        Args:
            namespace (str): Namespace value
        """
        self.namespace = namespace

    def get_status(self) -> Optional[str]:
        """
        Get the creation status.

        Returns:
            Optional[str]: Status value (READY, FAILED, etc.) or None
        """
        return self.status

    def set_status(self, status: str) -> None:
        """
        Set the creation status.

        Args:
            status (str): Status value
        """
        self.status = status

    def get_labels(self) -> dict:
        """
        Get all labels.

        Returns:
            dict: Labels dictionary
        """
        return self.labels

    def set_label(self, key: str, value: str) -> None:
        """
        Set a label.

        Args:
            key (str): Label key
            value (str): Label value
        """
        self.labels[key] = value

    def get_label(self, key: str) -> Optional[str]:
        """
        Get a specific label value.

        Args:
            key (str): Label key

        Returns:
            Optional[str]: Label value or None
        """
        return self.labels.get(key)
