class KubectlHelmObject:
    """Object representing a kubectl helmchart."""

    def __init__(self, name: str):
        """Initialize KubectlHelmObject.

        Args:
            name (str): Name of the helm.
        """
        self.name = name
        self.chart = None
        self.version = None

    def get_name(self) -> str:
        """Get helm name.

        Returns:
            str: Helm name.
        """
        return self.name

    def set_chart(self, chart: str) -> None:
        """Set chart name.

        Args:
            chart (str): Chart name.
        """
        self.chart = chart

    def get_chart(self) -> str:
        """Get chart name.

        Returns:
            str: Chart name.
        """
        return self.chart

    def set_version(self, version: str) -> None:
        """Set version.

        Args:
            version (str): Version value.
        """
        self.version = version

    def get_version(self) -> str:
        """Get version.

        Returns:
            str: Version value.
        """
        return self.version
