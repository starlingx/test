"""One parsed numeric interface metric sample."""


class InterfaceMetricSample:
    """Keep metric name, labels and value behind explicit accessors."""

    def __init__(self, name: str, labels: dict[str, str], value: float):
        """Initialize an already validated sample.

        Args:
            name (str): Metric family name.
            labels (dict[str, str]): Parsed identity labels.
            value (float): Finite numeric sample.
        """
        self.name = name
        self.labels = dict(labels)
        self.value = value

    def get_name(self) -> str:
        """Return the family name.

        Returns:
            str: Metric family name.
        """
        return self.name

    def get_labels(self) -> dict[str, str]:
        """Return a copy of the identity labels.

        Returns:
            dict[str, str]: Metric labels.
        """
        return dict(self.labels)

    def get_value(self) -> float:
        """Return the numeric sample.

        Returns:
            float: Parsed metric value.
        """
        return self.value
