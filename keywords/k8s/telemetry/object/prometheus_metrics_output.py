"""Output parser for Prometheus-format metrics."""

from typing import Dict, List, Optional


class PrometheusMetricsOutput:
    """Parses raw Prometheus metrics text into queryable data.

    Accepts a list of metric lines from a /metrics endpoint scrape
    and provides methods to extract values by name, prefix, or label.
    """

    def __init__(self, lines: List[str]) -> None:
        """Initialize with raw metric lines.

        Args:
            lines (List[str]): Raw lines from Prometheus /metrics endpoint.
        """
        self._lines = lines

    def get_lines(self) -> List[str]:
        """Get all raw metric lines.

        Returns:
            List[str]: All lines from the scrape output.
        """
        return self._lines

    def get_metric_sum(self, metric_name: str) -> Optional[float]:
        """Sum all values for a given metric name across label combinations.

        Args:
            metric_name (str): Full metric name.

        Returns:
            Optional[float]: Sum of all matching values, or None if not found.
        """
        total = 0.0
        found = False
        for line in self._lines:
            if self._is_data_line(line) and line.startswith(metric_name):
                value = self._parse_value(line)
                if value is not None:
                    total += value
                    found = True
        return total if found else None

    def get_metrics_by_prefix(self, prefix: str) -> Dict[str, float]:
        """Get all metrics matching a prefix as a dictionary.

        Args:
            prefix (str): Metric name prefix.

        Returns:
            Dict[str, float]: Dictionary of full metric line key to value.
        """
        metrics = {}
        for line in self._lines:
            if self._is_data_line(line) and line.startswith(prefix):
                parts = line.split()
                if len(parts) >= 2:
                    value = self._parse_value(line)
                    if value is not None:
                        metrics[parts[0]] = value
        return metrics

    def count_metrics_with_prefix(self, prefix: str) -> int:
        """Count how many metric data lines match a prefix.

        Args:
            prefix (str): Metric name prefix.

        Returns:
            int: Number of matching metric lines (excludes comments).
        """
        count = 0
        for line in self._lines:
            if self._is_data_line(line) and line.startswith(prefix):
                count += 1
        return count

    def get_metric_value_with_label(
        self, metric_name: str, label_name: str, label_value: str
    ) -> Optional[float]:
        """Get a metric value filtered by a specific label.

        Args:
            metric_name (str): Metric name prefix.
            label_name (str): Label key to filter by.
            label_value (str): Expected label value.

        Returns:
            Optional[float]: Value of the first matching metric, or None.
        """
        label_pattern = f'{label_name}="{label_value}"'
        for line in self._lines:
            if (
                self._is_data_line(line)
                and line.startswith(metric_name)
                and label_pattern in line
            ):
                value = self._parse_value(line)
                if value is not None:
                    return value
        return None

    def has_metric_with_label(
        self, metric_name: str, label_name: str, label_value: str
    ) -> bool:
        """Check if a metric exists with a specific label value.

        Args:
            metric_name (str): Metric name prefix.
            label_name (str): Label key to check.
            label_value (str): Expected label value.

        Returns:
            bool: True if at least one matching metric exists.
        """
        return (
            self.get_metric_value_with_label(metric_name, label_name, label_value)
            is not None
        )

    def _is_data_line(self, line: str) -> bool:
        """Check if a line is a data line (not a comment or empty).

        Args:
            line (str): Metric line.

        Returns:
            bool: True if the line contains metric data.
        """
        return bool(line) and not line.startswith("#")

    def _parse_value(self, line: str) -> Optional[float]:
        """Parse the numeric value from a metric line.

        Args:
            line (str): A Prometheus metric line (e.g. 'metric_name{labels} 42').

        Returns:
            Optional[float]: Parsed value, or None if parsing fails.
        """
        parts = line.split()
        if len(parts) >= 2:
            try:
                return float(parts[-1])
            except ValueError:
                return None
        return None

    def __str__(self) -> str:
        """Human-readable representation.

        Returns:
            str: Summary of metrics output.
        """
        return f"PrometheusMetricsOutput(lines={len(self._lines)})"
