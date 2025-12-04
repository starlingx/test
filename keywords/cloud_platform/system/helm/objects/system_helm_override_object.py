class HelmOverrideObject:
    """
    This class represents a helm override entry as an object.

    This is typically a line in the system helm override output table.
    """

    def __init__(self):
        """
        Constructor
        """
        self.name: str = None
        self.namespace: str = None

    def set_name(self, name: str):
        """
        Set the name of the helm override.

        Args:
            name (str): The name of the helm override entry.
        """
        self.name = name

    def get_name(self) -> str:
        """
        Get the name of the helm override.

        Returns:
            str: The name of the helm override entry.
        """
        return self.name

    def set_namespace(self, namespace: str):
        """
        Set the namespace for the helm override.

        Args:
            namespace (str): The Kubernetes namespace.
        """
        self.namespace = namespace

    def get_namespace(self) -> str:
        """
        Get the namespace of the helm override.

        Returns:
            str: The Kubernetes namespace.
        """
        return self.namespace
