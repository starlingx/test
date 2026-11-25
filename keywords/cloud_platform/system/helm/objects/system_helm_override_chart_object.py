from typing import List


class HelmOverrideChartObject:
    """
    This class represents one chart of the 'system helm-override-list <app>' output table.
    """

    def __init__(self, name: str, namespaces: List[str]):
        """
        Constructor

        Args:
            name (str): The chart name.
            namespaces (List[str]): The namespaces the chart has overrides for.
        """
        self.name = name
        self.namespaces = namespaces

    def get_name(self) -> str:
        """
        Get the chart name.

        Returns:
            str: The chart name.
        """
        return self.name

    def get_namespaces(self) -> List[str]:
        """
        Get the namespaces the chart has overrides for.

        Returns:
            List[str]: The namespaces.
        """
        return self.namespaces
