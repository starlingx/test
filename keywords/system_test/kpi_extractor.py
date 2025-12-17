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
        self.bash_log = '/var/log/bash.log'
        self.lock_action_pattern = "Lock Action"
        self.unlock_action_pattern = "Unlock Action"
        self.locked_disabled_online_pattern = "locked-disabled-online"
        self.enabled_pattern = "is ENABLED"
        self.available_pattern = "mtcClient ready ; with pxeboot mtcAlive support"
        self.timestamp_pattern = r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3})"
        self.timestamp_format = "%Y-%m-%dT%H:%M:%S.%f"
        self.unlock_to_available_pattern = "mtcClient ready"
        self.unlock_to_enabled_pattern = "is ENABLED ; from unlock"
        self.reboot_start_pattern = "unlocked-disabled-failed"

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
        end_timestamp = self._get_timestamp_from_pattern(end_pattern)

        time_diff = (end_timestamp - start_timestamp).total_seconds()
        if time_diff < 0:
            raise ValueError(f"Negative timing detected: {time_diff}s. End timestamp may be before start timestamp.")

        return time_diff

    def extract_unlock_to_available_timing(self, host_name: str) -> float:
        """
        Extract timing from unlock action to host available (mtcClient ready).

        Args:
            host_name: Name of the host to extract timing for

        Returns:
            Time in seconds from unlock to available

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = f'{host_name} {self.unlock_action_pattern}'
        end_pattern = f'{host_name} {self.unlock_to_available_pattern}'
        return self._extract_timing_between_patterns(start_pattern, end_pattern)

    def extract_unlock_to_enabled_timing(self, host_name: str) -> float:
        """
        Extract timing from unlock action to host enabled.

        Args:
            host_name: Name of the host to extract timing for

        Returns:
            Time in seconds from unlock to enabled

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = f'{host_name} {self.unlock_action_pattern}'
        end_pattern = f'{host_name} {self.unlock_to_enabled_pattern}'
        return self._extract_timing_between_patterns(start_pattern, end_pattern)

    def extract_reboot_to_available_timing(self, host_name: str) -> float:
        """
        Extract timing from reboot (unlocked-disabled-failed) to host available (mtcClient ready).

        Args:
            host_name: Name of the host to extract timing for

        Returns:
            Time in seconds from reboot to available

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = f'{host_name} {self.reboot_start_pattern}'
        end_pattern = f'{host_name} {self.unlock_to_available_pattern}'
        return self._extract_timing_between_patterns(start_pattern, end_pattern)

    def extract_reboot_to_enabled_timing(self, host_name: str) -> float:
        """
        Extract timing from reboot (unlocked-disabled-failed) to host enabled.

        Args:
            host_name: Name of the host to extract timing for

        Returns:
            Time in seconds from reboot to enabled

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = f'{host_name} {self.reboot_start_pattern}'
        end_pattern = f'{host_name} {self.enabled_pattern}'
        return self._extract_timing_between_patterns(start_pattern, end_pattern)

    def extract_max_timing_for_hosts(self, host_names: list, extract_method_name: str) -> float:
        """
        Extract timing for multiple hosts and return the maximum value.

        Args:
            host_names: List of host names
            extract_method_name: Name of the extraction method to call

        Returns:
            Maximum timing value across all hosts
        """
        max_timing = 0.0
        extract_method = getattr(self, extract_method_name)
        for host_name in host_names:
            timing = extract_method(host_name)
            if timing > max_timing:
                max_timing = timing
        return max_timing

    def _get_timestamp_from_pattern(self, pattern: str) -> datetime.datetime:
        """
        Get timestamp from log pattern.
        Uses tail -1 to get the most recent occurrence if multiple matches exist.

        Args:
            pattern: Pattern to search for in logs

        Returns:
            Parsed timestamp

        Raises:
            ValueError: If pattern not found or timestamp parsing fails
        """
        cmd = f"grep -a -E '{pattern}' {self.mtc_agent_log} | tail -1"
        output = self.ssh_connection.send(cmd)

        if not output or not output[0].strip():
            raise ValueError(f"Pattern not found in logs: {pattern}")

        match = re.search(self.timestamp_pattern, output[0])
        if not match:
            raise ValueError(f"Timestamp not found in log output for pattern '{pattern}': {output[0]}")

        return datetime.datetime.strptime(match.group(), self.timestamp_format)