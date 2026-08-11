"""Output object for Prometheus /api/v1/targets responses."""

import json
from typing import List


class PrometheusTargetsOutput:
    """Represents the response from the Prometheus /api/v1/targets endpoint.

    Wraps the raw JSON response and provides methods to check for
    healthy scrape targets by job name.
    """

    def __init__(self, raw_output: str) -> None:
        """Initialize with raw API response string.

        Args:
            raw_output (str): Raw string response from /api/v1/targets.
        """
        self._raw = raw_output
        self._parsed = None
        try:
            self._parsed = json.loads(raw_output)
        except (json.JSONDecodeError, TypeError):
            pass

    def get_raw_response(self) -> str:
        """Get the raw JSON response string.

        Returns:
            str: The raw response from /api/v1/targets.
        """
        return self._raw

    def get_active_targets(self) -> List[dict]:
        """Get the list of active scrape targets.

        Returns:
            List[dict]: Active targets from the response, or empty list.
        """
        if not self._parsed:
            return []
        return self._parsed.get("data", {}).get("activeTargets", [])

    def get_healthy_jobs(self) -> List[str]:
        """Get job names of all healthy (up) active targets.

        Returns:
            List[str]: Unique job names where health == 'up'.
        """
        healthy = set()
        for target in self.get_active_targets():
            if target.get("health") == "up":
                job = target.get("labels", {}).get("job", "")
                if job:
                    healthy.add(job)
        return sorted(healthy)

    def has_healthy_job(self, job_prefix: str) -> bool:
        """Check if any healthy target has a job name matching the prefix.

        Args:
            job_prefix (str): Prefix to match against job names.

        Returns:
            bool: True if at least one healthy target matches.
        """
        for target in self.get_active_targets():
            if target.get("health") == "up":
                job = target.get("labels", {}).get("job", "")
                if job.startswith(job_prefix):
                    return True
        return False

    def has_all_healthy_jobs(self, job_prefixes: List[str]) -> bool:
        """Check if all specified job prefixes have at least one healthy target.

        Args:
            job_prefixes (list[str]): List of job name prefixes that must
                each have at least one healthy target.

        Returns:
            bool: True if every prefix has at least one healthy match.
        """
        return all(self.has_healthy_job(prefix) for prefix in job_prefixes)

    def is_failed(self) -> bool:
        """Check if the targets query failed entirely.

        Returns:
            bool: True if no usable response was received.
        """
        return self._parsed is None or self._parsed.get("status") != "success"

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Summary of targets output.
        """
        healthy = self.get_healthy_jobs()
        total = len(self.get_active_targets())
        return f"PrometheusTargetsOutput(active={total}, healthy_jobs={healthy})"
