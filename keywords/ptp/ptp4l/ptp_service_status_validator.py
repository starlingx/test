import re
from datetime import datetime, timedelta, timezone
from multiprocessing import get_logger

from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.linux.systemctl.systemctl_status_keywords import SystemCTLStatusKeywords
from keywords.ptp.ptp4l.objects.ptp4l_status_output import PTP4LStatusOutput


class PTPServiceStatusValidator(BaseKeyword):
    """
    A class to validate the status and parameters of PTP (Precision Time Protocol)
    services on a target host using systemctl.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initializes the PTPServiceStatusValidator with an SSH connection.

        Args:
            ssh_connection: An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def verify_status_on_hostname(self, hostname: str, name: str, service_name: str) -> None:
        """
        verify systemctl ptp service status on hostname

        Args:
            hostname (str): The name of the host
            name (str): name of instance (e.g., "phc1")
            service_name (str): service name (e.g., "phc2sys@phc1.service")

        Returns: None

        Raises:
            Exception: raised when validate fails
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_ssh_for_hostname(hostname)

        output = SystemCTLStatusKeywords(ssh_connection).get_status(service_name)
        ptp_service_status_output = PTP4LStatusOutput(output)
        expected_service_status = "active (running)"
        observed_service_status = ptp_service_status_output.get_ptp4l_object(name).get_active()

        validate_str_contains(observed_service_status, expected_service_status, f"systemctl status {service_name}")

    def verify_status_and_instance_parameters_on_hostname(self, hostname: str, name: str, service_name: str, instance_parameters: str) -> None:
        """
        verify systemctl service status and instance parameters on hostname

        Args:
            hostname (str): The name of the host
            name (str) : name of instance (e.g., "phc1")
            service_name (str): service name (e.g., "phc2sys@phc1.service")
            instance_parameters (str) : instance parameters

        Returns: None

        Raises:
            Exception: raised when validate fails
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_ssh_for_hostname(hostname)

        output = SystemCTLStatusKeywords(ssh_connection).get_status(service_name)
        service_status_output = PTP4LStatusOutput(output)

        expected_service_status = "active (running)"
        observed_service_status = service_status_output.get_ptp4l_object(name).get_active()
        get_command = service_status_output.get_ptp4l_object(name).get_command()

        # From the input string "cmdline_opts='-s enpXXs0f2 -O -37 -m'"
        # The extracted output string is '-s enpXXs0f2 -O -37 -m'
        instance_parameter = eval(instance_parameters.split("=")[1])

        if expected_service_status in observed_service_status and instance_parameter in get_command:
            get_logger().log_info(f"Validation Successful - systemctl status {service_name}")
        else:
            get_logger().log_info(f"Validation Failed - systemctl status {service_name}")
            get_logger().log_info(f"Expected service status: {expected_service_status}")
            get_logger().log_info(f"Observed service status: {observed_service_status}")
            get_logger().log_info(f"Expected instance parameter: {instance_parameter}")
            get_logger().log_info(f"Observed instance parameter: {get_command}")
            raise Exception("Validation Failed")

    def _is_service_event_recent(self, status_line: str, threshold_seconds: int) -> bool:
        """
        Determines if a service event (start, stop, restart) occurred within a given threshold.

        Args:
            status_line (str): A line like:
                'active (running) since Wed 2025-05-28 13:00:00 UTC; 10s ago'
                'inactive (dead) since Wed 2025-05-28 12:22:49 UTC; 52min ago'
            threshold_seconds (int): Time threshold in seconds.

        Returns:
            bool: True if the event occurred within the threshold.
        """
        match = re.search(r"since (.+? UTC);\s+(\d+)(s|min|h) ago", status_line)
        if not match:
            raise ValueError(f"Could not parse systemctl status line: {status_line}")

        datetime_str, value_str, unit = match.groups()

        try:
            datetime.strptime(datetime_str.strip(), "%a %Y-%m-%d %H:%M:%S UTC")
        except ValueError:
            raise ValueError(f"Could not parse timestamp: {datetime_str.strip()}")

        # Convert "52min" or "10s" into timedelta
        value = int(value_str)
        if unit == "s":
            delta = timedelta(seconds=value)
        elif unit == "min":
            delta = timedelta(minutes=value)
        elif unit == "h":
            delta = timedelta(hours=value)
        else:
            raise ValueError(f"Unsupported time unit: {unit}")

        # Estimate the actual event time from 'ago'
        now = datetime.now(timezone.utc)
        estimated_event_time = now - delta

        # Compare time difference
        return (now - estimated_event_time).total_seconds() <= threshold_seconds

    def verify_service_status_and_recent_event(self, service_name: str, instance_name: str, threshold_seconds: int, expected_service_status: str = "active (running)") -> None:
        """
        Verifies that the given PTP service is in the expected systemctl status and
        that its most recent state change occurred within the given threshold.

        Args:
            service_name (str): service name (e.g., "phc2sys")
            instance_name (str): name of instance (e.g., "phc1")
            threshold_seconds (int): Time threshold in seconds to check service recency.
            expected_service_status (str, optional): Expected status string to match from `systemctl` (default: "active (running)").

        Returns: None

        Raises:
            Exception: If service status is not as expected, or event is too old.
        """
        template_instance = f"{service_name}@{instance_name}.service"
        output = SystemCTLStatusKeywords(self.ssh_connection).get_status(template_instance)
        service_status_output = PTP4LStatusOutput(output)
        service_status = service_status_output.get_ptp4l_object(instance_name)

        status_line = service_status.get_active()

        # Check if the service event (start/stop/restart) was recent
        recent_event = self._is_service_event_recent(status_line, threshold_seconds)
        validate_equals(recent_event, True, "Service event recency check")

        # Validate actual status
        validate_str_contains(status_line, expected_service_status, f"systemctl status {template_instance}")
