import ast


class HelmChartAttributeModifyObject:
    """
    Represents a single Helm chart attribute modification entry extracted from the
    'system helm-chart-attribute-modify' command output.
    """

    def __init__(self):
        """
        Constructor
        """
        self.name: str = None
        self.namespace: str = None
        self.attributes: dict = None

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

    def set_attributes(self, attributes_str: str):
        """
        Sets the attributes for the Helm chart.
        Converts string attributes like "{'enabled': True}" into a dict.
        Args:
            attributes (str): Attributes str).
        """

        if isinstance(attributes_str, str):
            try:
                self.attributes = ast.literal_eval(attributes_str)
            except Exception:
                self.attributes = {}
        elif isinstance(attributes_str, dict):
            self.attributes = attributes_str
        else:
            self.attributes = {}

    def get_attributes(self) -> dict:
        """
        Gets the attributes for the Helm chart.

        Returns:
            dict: Attributes dictionary.
        """
        return self.attributes
