"""Output object for Prometheus HTTP API query responses."""

import json
from typing import Dict, List


class PrometheusApiQueryOutput:
    """Represents the response from a Prometheus HTTP API query.

    Wraps the raw JSON response string from /api/v1/query or
    /api/v1/query_range and provides methods to check for data
    presence without exposing raw string parsing to callers.
    """

    def __init__(self, raw_output: str) -> None:
        """Initialize with raw API response string.

        Args:
            raw_output (str): Raw string response from the Prometheus API.
        """
        self._raw = raw_output
        self._parsed = None
        try:
            self._parsed = json.loads(raw_output)
        except (json.JSONDecodeError, TypeError):
            pass

    def get_response(self) -> Dict:
        """Return the successful response document for artifact generation.

        Returns:
            Dict: Original API response, retaining labels and samples.

        Raises:
            ValueError: If the API response failed or lacks a result list.
        """
        if not isinstance(self._parsed, dict) or self._parsed.get("status") != "success":
            raise ValueError(f"Prometheus query failed: {self._parsed}")
        data = self._parsed.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("result"), list):
            raise ValueError("Prometheus query response has no valid result list")
        return self._parsed

    def get_series(self) -> List[Dict]:
        """Return labeled series from a successful Prometheus response.

        Returns:
            List[Dict]: Original metric labels and timestamped samples.

        Raises:
            ValueError: If the response is unsuccessful or malformed.
        """
        return self.get_response()["data"]["result"]

    def has_data(self) -> bool:
        """Check if the response contains metric data.

        Returns:
            bool: True if the response indicates a successful instant query with values.
        """
        if not self._parsed:
            return False
        try:
            return self._parsed.get("status") == "success" and any(r.get("value") for r in self._parsed.get("data", {}).get("result", []))
        except (AttributeError, TypeError):
            return False

    def has_range_data(self) -> bool:
        """Check if the response contains range query metric data.

        Returns:
            bool: True if the response indicates a successful range query with values.
        """
        if not self._parsed:
            return False
        try:
            return self._parsed.get("status") == "success" and any(r.get("values") for r in self._parsed.get("data", {}).get("result", []))
        except (AttributeError, TypeError):
            return False

    def contains_timestamp(self, timestamp: int) -> bool:
        """Check if the response contains any data point at or after the given timestamp.

        Used to verify that new scrapes have occurred after a given point in time.

        Args:
            timestamp (int): Unix timestamp. Returns True if any data point
                has a timestamp >= this value.

        Returns:
            bool: True if a data point at or after the timestamp exists.
        """
        if not self._parsed:
            return False
        try:
            for result in self._parsed.get("data", {}).get("result", []):
                for value in result.get("values", []):
                    if float(value[0]) >= timestamp:
                        return True
        except (KeyError, IndexError, TypeError, ValueError):
            pass
        return False

    def is_failed(self) -> bool:
        """Check if the query failed entirely (no API response).

        Returns:
            bool: True if the query returned no usable response.
        """
        return self._parsed is None or self._parsed.get("status") != "success"

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Summary of the query output.
        """
        return f"PrometheusApiQueryOutput(has_data={self.has_data()}, has_range_data={self.has_range_data()})"
