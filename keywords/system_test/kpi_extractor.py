import datetime
import re
from typing import Optional
import time
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
            ssh_connection (SSHConnection): SSH connection to the target system
        """
        self.ssh_connection = ssh_connection
        self.mtc_agent_log = "/var/log/mtcAgent.log"
        self.bash_log = "/var/log/bash.log"
        self.lock_action_pattern = "Lock Action"
        self.unlock_action_pattern = "Unlock Action"
        self.locked_disabled_online_pattern = "locked-disabled-online"
        self.enabled_pattern = "is ENABLED"
        self.available_pattern = "mtcClient ready ; with pxeboot mtcAlive support"
        self.timestamp_pattern = r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3})"
        self.timestamp_format = "%Y-%m-%dT%H:%M:%S.%f"
        self.unlock_to_available_pattern = "mtcClient ready"
        self.unlock_to_enabled_pattern = "is ENABLED ; from unlock"
        self.reboot_start_pattern = "Received SIGINT"
        self.dor_recovery_pattern = "is ENABLED  ; DOR Recovery"
        self.check_interval = 10
        self.worker_available_pattern = "mtcClient start worker host services ran and passed"
        self.worker_reboot_start_pattern = "heartbeat degrade set \(Mgmnt\)"
        self.worker_enabled_pattern = "is ENABLED \(Gracefully Recovered\)"
        self.sm_customer_log = '/var/log/sm-customer.log'
        self.swact_start_pattern = "node-scn"
        self.swact_end_pattern = "service-group-scn\s+\|\s+controller-services\s+\|\s+go-active\s+\|\s+active"
        self.uncontrolled_swact_start_pattern = "service-group-scn\s+\|\s+controller-services\s+\|\s+standby\s+\|\s+go-active"

    def extract_lock_timing(self, host_name: str) -> float:
        """
        Extract lock timing for a specific host from logs.

        Uses the most recent (last) occurrence if multiple lock operations exist.

        Args:
            host_name(str): Name of the host to extract timing for

        Returns:
            float: Lock timing in seconds

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = f"{host_name} {self.lock_action_pattern}"
        end_pattern = f"{host_name} {self.locked_disabled_online_pattern}"
        return self._extract_timing_between_patterns(start_pattern, end_pattern)

    def extract_unlock_timing(self, host_name: str) -> float:
        """
        Extract unlock timing for a specific host from logs.

        Uses the most recent (last) occurrence if multiple unlock operations exist.

        Args:
            host_name(str): Name of the host to extract timing for

        Returns:
            float: Unlock timing in seconds

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = f"{host_name} {self.unlock_action_pattern}"
        end_pattern = f"{host_name} {self.enabled_pattern}"
        return self._extract_timing_between_patterns(start_pattern, end_pattern)

    def _extract_timing_between_patterns(self, start_pattern: str, end_pattern: str) -> float:
        """
        Extract timing between two log patterns.

        Uses the most recent (last) occurrence of each pattern independently.

        Args:
            start_pattern(str): Pattern to search for start timestamp
            end_pattern(str): Pattern to search for end timestamp

        Returns:
            float: Time difference in seconds

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_timestamp = self._get_timestamp_from_pattern(start_pattern)
        end_timestamp = self._get_timestamp_from_pattern(end_pattern)

        get_logger().log_info(f"Start pattern: '{start_pattern}' -> Timestamp: {start_timestamp}")
        get_logger().log_info(f"End pattern: '{end_pattern}' -> Timestamp: {end_timestamp}")

        time_diff = (end_timestamp - start_timestamp).total_seconds()
        if time_diff < 0:
            raise ValueError(f"Negative timing detected: {time_diff}s. End timestamp may be before start timestamp.")

        return time_diff

    def extract_unlock_to_available_timing(self, host_name: str) -> float:
        """
        Extract timing from unlock action to host available (mtcClient ready).

        Args:
            host_name(str): Name of the host to extract timing for

        Returns:
            float: Time in seconds from unlock to available

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = f"{host_name} {self.unlock_action_pattern}"
        end_pattern = f"{host_name} {self.unlock_to_available_pattern}"
        return self._extract_timing_between_patterns(start_pattern, end_pattern)

    def extract_unlock_to_enabled_timing(self, host_name: str) -> float:
        """
        Extract timing from unlock action to host enabled.

        Args:
            host_name(str): Name of the host to extract timing for

        Returns:
            float: Time in seconds from unlock to enabled

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = f"{host_name} {self.unlock_action_pattern}"
        end_pattern = f"{host_name} {self.unlock_to_enabled_pattern}"
        return self._extract_timing_between_patterns(start_pattern, end_pattern)

    def extract_reboot_to_available_timing(self, host_name: str) -> float:
        """
        Extract timing from reboot (Received SIGINT) to host available (mtcClient ready).

        Args:
            host_name(str): Name of the host to extract timing for

        Returns:
            float: Time in seconds from reboot to available

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = f"{host_name}.*{self.reboot_start_pattern}"
        end_pattern = f"{host_name} {self.unlock_to_available_pattern}"
        return self._extract_timing_between_patterns(start_pattern, end_pattern)

    def extract_reboot_to_enabled_timing(self, host_name: str) -> float:
        """
        Extract timing from reboot (Received SIGINT) to host enabled (is Enabled).

        Args:
            host_name(str): Name of the host to extract timing for

        Returns:
            float: Time in seconds from reboot to enabled

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = f"{host_name}.*{self.reboot_start_pattern}"
        end_pattern = f"{host_name} {self.enabled_pattern}"
        return self._extract_timing_between_patterns(start_pattern, end_pattern)

    def extract_dor_recovery_timing(self, host_name: str, wait_timeout: int = 60) -> float:
        """
        Extract DOR (Dead Office Recovery) timing from log message.

        Parses the embedded seconds value from "DOR Recovery X:XX mins ( NNN secs)".

        Args:
            host_name(str): Name of the host to extract timing for
            wait_timeout(int): Maximum time to wait for pattern to appear in logs (seconds)

        Returns:
            float: DOR recovery time in seconds

        Raises:
            ValueError: If pattern not found or extraction fails
        """
        pattern = f"{host_name} {self.dor_recovery_pattern}"
        start_time = time.time()
        
        while time.time() - start_time < wait_timeout:
            cmd = f"grep -a -E '{pattern}' {self.mtc_agent_log} | tail -1"
            output = self.ssh_connection.send(cmd)

            if output and output[0].strip():
                match = re.search(r"\(\s*(\d+)\s*secs\)", output[0])
                if match:
                    return float(match.group(1))
            
            if time.time() - start_time < wait_timeout:
                get_logger().log_debug(f"DOR recovery pattern '{pattern}' not found yet, waiting {self.check_interval}s...")
                time.sleep(self.check_interval)
        
        raise ValueError(f"DOR recovery pattern not found in logs within {wait_timeout}s: {pattern}")

    def extract_worker_reboot_to_available_timing(self, host_name: str) -> float:
        """
        Extract timing from reboot (unlocked-disabled-failed) to host available (mtcClient ready).

        Args:
            host_name: Name of the host to extract timing for

        Returns:
            Time in seconds from reboot to available

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = f'{host_name} {self.worker_reboot_start_pattern}'
        end_pattern = f'{host_name} {self.worker_available_pattern}'
        return self._extract_timing_between_patterns(start_pattern, end_pattern)
    
    def extract_worker_reboot_to_enabled_timing(self, host_name: str) -> float:
        """
        Extract timing from reboot (starting graceful recovery) to host enabled (Gracefully Recovered).

        Args:
            host_name: Name of the host to extract timing for

        Returns:
            Time in seconds from reboot to enabled

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = f'{host_name} {self.worker_reboot_start_pattern}'
        end_pattern = f'{host_name} {self.worker_enabled_pattern}'
        return self._extract_timing_between_patterns(start_pattern, end_pattern)


    def extract_max_timing_for_hosts(self, host_names: list, extract_method_name: str) -> float:
        """
        Extract timing for multiple hosts and return the maximum value.

        Args:
            host_names(list): List of host names
            extract_method_name(str): Name of the extraction method to call

        Returns:
            float: Maximum timing value across all hosts
        """
        max_timing = 0.0
        extract_method = getattr(self, extract_method_name)
        for host_name in host_names:
            timing = extract_method(host_name)
            if timing > max_timing:
                max_timing = timing
        return max_timing

    def _get_timestamp_from_pattern(self, pattern: str, wait_timeout: int = 180) -> datetime.datetime:
        """
        Get timestamp from log pattern.

        Uses tail -1 to get the most recent (last) occurrence.
        Retries for up to wait_timeout seconds if pattern not found.

        Args:
            pattern(str): Pattern to search for in logs
            wait_timeout(int): Maximum time to wait for pattern to appear in logs (seconds)

        Returns:
            datetime.datetime: Parsed timestamp

        Raises:
            ValueError: If pattern not found or timestamp parsing fails
        """
        start_time = time.time()
        
        while time.time() - start_time < wait_timeout:
            output = self._search_pattern_in_logs(pattern)
            
            if output:
                timestamp = self._extract_timestamp_from_line(output[0])
                if timestamp:
                    return timestamp
            
            if time.time() - start_time < wait_timeout:
                get_logger().log_debug(f"Pattern '{pattern}' not found yet, waiting {self.check_interval}s...")
                time.sleep(self.check_interval)
        
        raise ValueError(f"Pattern not found in logs within {wait_timeout}s: {pattern}")

    def _search_pattern_in_logs(self, pattern: str) -> list:
        """
        Search for pattern in log files.

        Gets only the most recent (last) occurrence using tail -1.

        Args:
            pattern(str): Pattern to search for

        Returns:
            list: Log lines matching the pattern

        """
        cmd = f"grep -a -E '{pattern}' {self.mtc_agent_log} | tail -1"
        output = self.ssh_connection.send(cmd)
        
        if output and len(output) > 0 and output[0]:
            return output
        return []

    def _extract_timestamp_from_line(self, log_line: str) -> Optional[datetime.datetime]:
        """
        Extract timestamp from a single log line.

        Args:
            log_line(str): Log line to extract timestamp from

        Returns:
            Optional[datetime.datetime]: Extracted timestamp, or None if not found

        """
        get_logger().log_info(f"Found log line: {log_line[:200]}...")
        match = re.search(self.timestamp_pattern, log_line)
        if match:
            return datetime.datetime.strptime(match.group(), self.timestamp_format)
        return None

    def extract_swact_timing(self, standby_controller_name: str) -> float:
        """
        Extract controlled swact timing from sm-customer.log.

        Args:
            standby_controller_name: Name of the standby controller that becomes active

        Returns:
            Swact timing in seconds

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = f'node-scn\s+\|\s+{standby_controller_name}\s+\|\s+\|\s+swact'
        end_pattern = self.swact_end_pattern
        return self._extract_timing_from_sm_log(start_pattern, end_pattern)

    def extract_uncontrolled_swact_timing(self) -> float:
        """
        Extract uncontrolled swact timing from sm-customer.log.

        Returns:
            Uncontrolled swact timing in seconds

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_pattern = self.uncontrolled_swact_start_pattern
        end_pattern = self.swact_end_pattern
        return self._extract_timing_from_sm_log(start_pattern, end_pattern)

    def _extract_timing_from_sm_log(self, start_pattern: str, end_pattern: str) -> float:
        """
        Extract timing between two patterns from sm-customer.log.

        Args:
            start_pattern: Pattern to search for start timestamp
            end_pattern: Pattern to search for end timestamp

        Returns:
            Time difference in seconds

        Raises:
            ValueError: If patterns not found or extraction fails
        """
        start_timestamp = self._get_timestamp_from_sm_log(start_pattern)
        end_timestamp = self._get_timestamp_from_sm_log(end_pattern)

        time_diff = (end_timestamp - start_timestamp).total_seconds()
        if time_diff < 0:
            raise ValueError(f"Negative timing detected: {time_diff}s. End timestamp may be before start timestamp.")

        return time_diff

    def _get_timestamp_from_sm_log(self, pattern: str) -> datetime.datetime:
        """
        Get timestamp from sm-customer.log pattern.

        Args:
            pattern: Pattern to search for in logs

        Returns:
            Parsed timestamp

        Raises:
            ValueError: If pattern not found or timestamp parsing fails
        """
        cmd = f"grep -a -E '{pattern}' {self.sm_customer_log} | tail -1"
        output = self.ssh_connection.send(cmd)

        if not output or not output[0].strip():
            raise ValueError(f"Pattern not found in sm-customer.log: {pattern}")

        match = re.search(self.timestamp_pattern, output[0])
        if not match:
            raise ValueError(f"Timestamp not found in log output for pattern '{pattern}': {output[0]}")

        return datetime.datetime.strptime(match.group(), self.timestamp_format)