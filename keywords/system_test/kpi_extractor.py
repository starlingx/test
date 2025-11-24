import datetime
import re
from typing import Optional

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection


class KpiExtractor:
    """
    Utility class to extract timing information from system log files.

    This class provides functionality to parse log files and calculate timing
    differences between start and end events based on predefined patterns.

    Example:
        >>> ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        >>> extractor = KpiExtractor(ssh_connection)
        >>> lock_time = extractor.extract_lock_timing("controller-1")
        >>> unlock_time = extractor.extract_unlock_timing("controller-1")
        >>> print(f"Lock took {lock_time:.2f}s, unlock took {unlock_time:.2f}s")
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Initialize the KpiExtractor.

        Args:
            ssh_connection: SSH connection to the target system
        """
        self.ssh_connection = ssh_connection
        self.mtc_agent_log = '/var/log/mtcAgent.log'
        self.lock_action_pattern = "Lock Action"
        self.unlock_action_pattern = "Unlock Action"
        self.locked_disabled_online_pattern = "locked-disabled-online"
        self.enabled_pattern = "is ENABLED"
        self.timestamp_pattern = r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3})"
        self.timestamp_format = "%Y-%m-%dT%H:%M:%S.%f"

    def extract_lock_timing(self, host_name: str) -> float:
        """
        Extract lock timing for a specific host from logs.
        Uses the most recent (last) occurrence if multiple lock operations exist.

        Args:
            host_name: Name of the host to extract timing for

        Returns:
            Lock timing in seconds
  
        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = f'{host_name} {self.lock_action_pattern}'
        end_pattern = f'{host_name} {self.locked_disabled_online_pattern}'
        return self._extract_timing_between_patterns(start_pattern, end_pattern)

    def extract_unlock_timing(self, host_name: str) -> float:
        """
        Extract unlock timing for a specific host from logs.
        Uses the most recent (last) occurrence if multiple unlock operations exist.

        Args:
            host_name: Name of the host to extract timing for

        Returns:
            Unlock timing in seconds
  
        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = f'{host_name} {self.unlock_action_pattern}'
        end_pattern = f'{host_name} {self.enabled_pattern}'
        return self._extract_timing_between_patterns(start_pattern, end_pattern)

    def _extract_timing_between_patterns(self, start_pattern: str, end_pattern: str) -> float:
        """
        Extract timing between two log patterns.
        Uses the most recent occurrence of each pattern.

        Args:
            start_pattern: Pattern to search for start timestamp
            end_pattern: Pattern to search for end timestamp

        Returns:
            Time difference in seconds

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_timestamp = self._get_timestamp_from_pattern(start_pattern)
        if not start_timestamp:
            raise ValueError(f"Start pattern not found in logs: {start_pattern}")

        end_timestamp = self._get_timestamp_from_pattern(end_pattern)
        if not end_timestamp:
            raise ValueError(f"End pattern not found in logs: {end_pattern}")

        time_diff = (end_timestamp - start_timestamp).total_seconds()
        if time_diff < 0:
            raise ValueError(f"Negative timing detected: {time_diff}s. End timestamp may be before start timestamp.")

        return time_diff

    def _get_timestamp_from_pattern(self, pattern: str) -> Optional[datetime.datetime]:
        """
        Get timestamp from log pattern.
        Uses tail -1 to get the most recent occurrence if multiple matches exist.

        Args:
            pattern: Pattern to search for in logs

        Returns:
            Parsed timestamp or None if pattern not found
        """
        cmd = f"grep -a -E '{pattern}' {self.mtc_agent_log} | tail -1"
        output = self.ssh_connection.send(cmd)

        if not output or not output[0].strip():
            return None

        match = re.search(self.timestamp_pattern, output[0])
        if not match:
            return None

        try:
            return datetime.datetime.strptime(match.group(), self.timestamp_format)
        except ValueError as e:
            get_logger().log_warning(f"Failed to parse timestamp '{match.group()}': {e}")
            return None