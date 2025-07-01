class KubectlRawMetricObject:
    """
    Class representing a raw metric object from Kubernetes metrics.
    """

    def __init__(self):
        """
        Constructor

        """
        self.metric = None
        self.labels = {}
        self.value = None

    def set_metric(self, metric: str):
        """
        Set the deprecated API metric.

        Args:
            metric (str): The deprecated API metric.
        """
        self.metric = metric

    def get_metric(self) -> str:
        """
        Get the deprecated API metric.

        Returns:
            str: The deprecated API metric.
        """
        return self.metric

    def set_labels(self, labels: dict):
        """
        Set the labels for the deprecated API metric.

        Args:
            labels (dict): The labels for the deprecated API metric.
        """
        self.labels = labels

    def get_labels(self) -> dict:
        """
        Get the labels for the deprecated API metric.

        Returns:
            dict: The labels for the deprecated API metric.
        """
        return self.labels

    def set_value(self, value: str):
        """
        Set the value for the deprecated API metric.

        Args:
            value (str): The value for the deprecated API metric.
        """
        self.value = value

    def get_value(self) -> str:
        """
        Get the value for the deprecated API metric.

        Returns:
            str: The value for the deprecated API metric.
        """
        return self.value
