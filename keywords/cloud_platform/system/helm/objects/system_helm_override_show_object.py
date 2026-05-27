import yaml

from framework.logging.automation_logger import get_logger


class HelmOverrideShowObject:
    """
    Represents a single Helm override entry extracted from the 'system helm-override-show' command output.
    """

    def __init__(self):
        """
        Initializes the HelmOverrideShowObject with default None values for all fields.
        """
        self.name: str = None
        self.namespace: str = None
        self.attributes: dict = None
        self.combined_overrides: dict = None
        self.system_overrides: dict = None
        self.user_overrides: str = None

    def set_name(self, name: str):
        """
        Sets the name of the Helm chart.

        Args:
            name (str): The name of the Helm chart.
        """
        self.name = name

    def get_name(self) -> str:
        """
        Gets the name of the Helm chart.

        Returns:
            str: The name of the Helm chart.
        """
        return self.name

    def set_namespace(self, namespace: str):
        """
        Sets the namespace of the Helm chart.

        Args:
            namespace (str): The Kubernetes namespace where the chart is deployed.
        """
        self.namespace = namespace

    def get_namespace(self) -> str:
        """
        Gets the namespace of the Helm chart.

        Returns:
            str: The Kubernetes namespace where the chart is deployed.
        """
        return self.namespace

    def set_attributes(self, attributes: dict):
        """
        Sets the attributes for the Helm chart.

        Args:
            attributes (dict): Attributes dictionary (e.g., {'enabled': True}).
        """
        self.attributes = attributes

    def get_attributes(self) -> dict:
        """
        Gets the attributes for the Helm chart.

        Returns:
            dict: Attributes dictionary.
        """
        return self.attributes

    def set_combined_overrides(self, combined_overrides: dict):
        """
        Sets the combined overrides (merged system and user) for the chart.

        Args:
            combined_overrides (dict): Combined override values in dictionary format.
        """
        self.combined_overrides = combined_overrides

    def get_combined_overrides(self) -> dict:
        """
        Gets the combined overrides for the chart.

        Returns:
            dict: Combined override values.
        """
        return self.combined_overrides

    def set_system_overrides(self, system_overrides: dict):
        """
        Sets the system-defined overrides for the chart.

        Args:
            system_overrides (dict): System overrides in dictionary format.
        """
        self.system_overrides = system_overrides

    def get_system_overrides(self) -> dict:
        """
        Gets the system-defined overrides for the chart.

        Returns:
            dict: System overrides dictionary.
        """
        return self.system_overrides

    def set_user_overrides(self, user_overrides: dict):
        """
        Sets the user-defined overrides for the chart.

        Args:
            user_overrides (dict): User override values in dictionary format.
        """
        self.user_overrides = user_overrides

    def get_user_overrides(self) -> str:
        """
        Gets the user-defined overrides for the chart.

        Returns:
            str: User override values.
        """
        return self.user_overrides

    def user_overrides_match(self, desired: str) -> bool:
        """Compare the current user overrides against a desired YAML string.

        Parses both strings with yaml.safe_load() and compares the resulting
        Python data structures using == (deep equality). This makes the comparison
        immune to whitespace, comment, key-ordering, and scalar-representation
        differences.

        Args:
            desired (str): The desired override YAML string to compare against.

        Returns:
            bool: True if the current user overrides match the desired, False otherwise.
        """
        current = self.user_overrides
        desired_empty = desired is None or desired.strip() == ""
        current_empty = current is None or not current.strip()

        if desired_empty and current_empty:
            return True

        if desired_empty or current_empty:
            return False

        try:
            desired_data = yaml.safe_load(desired)
        except yaml.YAMLError as e:
            get_logger().log_warning(
                f"Failed to parse desired YAML for override comparison: {e}"
            )
            return False

        try:
            current_data = yaml.safe_load(current)
        except yaml.YAMLError as e:
            get_logger().log_warning(
                f"Failed to parse current YAML for override comparison: {e}"
            )
            return False

        return desired_data == current_data
