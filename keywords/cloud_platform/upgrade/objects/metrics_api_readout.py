class MetricsApiReadout:
    """One snapshot of the three Metrics-API reads, so the probe does not shuttle a tuple.

    Holds the APIService Available condition value and whether each `kubectl top` read served a
    parseable reading. Exposes typed getters rather than fields, as the framework requires.
    """

    def __init__(self, available: str, top_nodes_served: bool, top_pods_served: bool):
        """Store one snapshot of the three reads.

        Args:
            available (str): the APIService Available condition value ("True" when serving).
            top_nodes_served (bool): whether `kubectl top nodes` served a parseable, non-zero reading.
            top_pods_served (bool): whether `kubectl top pods` served a parseable reading.
        """
        self.available = available
        self.top_nodes_served = top_nodes_served
        self.top_pods_served = top_pods_served

    def get_available(self) -> str:
        """Return the APIService Available condition value.

        Returns:
            str: the Available condition value, "True" when the APIService is serving.
        """
        return self.available

    def is_top_nodes_served(self) -> bool:
        """Return whether `kubectl top nodes` served a parseable, non-zero reading.

        Returns:
            bool: True when a node reading was served.
        """
        return self.top_nodes_served

    def is_top_pods_served(self) -> bool:
        """Return whether `kubectl top pods` served a parseable reading.

        Returns:
            bool: True when a pod reading was served.
        """
        return self.top_pods_served

    def is_fully_served(self) -> bool:
        """Return whether all three reads are served.

        Returns:
            bool: True when the APIService is Available and both `top` reads served a reading.
        """
        return self.available == "True" and self.top_nodes_served and self.top_pods_served

    def __str__(self) -> str:
        """Return a human-readable snapshot for logging.

        Returns:
            str: the three read results in one line.
        """
        return f"MetricsApiReadout(available={self.available!r}, top_nodes_served={self.top_nodes_served}, top_pods_served={self.top_pods_served})"
