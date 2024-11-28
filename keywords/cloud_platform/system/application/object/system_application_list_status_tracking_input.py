from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.python.string import String


class SystemApplicationListStatusTrackingInput:
    """
    This class is intended to create instances for the argument of SystemApplicationApplyKeywords.track_status() method.
    That method will check every 'time_in_seconds' whether 'app_name' has reached the 'expected_status' before the total
    elapsed time since the method was called reaches 'time_in_seconds'. The 'operation_name' can assume the following
    values: 'Applying', 'Updating', or 'Removing'.
    """

    def __init__(self, app_name: str, expected_status: SystemApplicationStatusEnum):
        """
        Constructor.
        """
        self.timeout_in_seconds = 60
        self.check_interval_in_seconds = 3

        if expected_status not in SystemApplicationStatusEnum:
            message = "The property 'expected_status' must be specified with a valid value."
            get_logger().log_info(message)
            raise ValueError(message)
        self.expected_status: SystemApplicationStatusEnum = expected_status

        self.app_name = app_name
        if String.is_empty(app_name):
            message = "The property 'app_name' must be specified."
            get_logger().log_info(message)
            raise ValueError(message)

    def set_timeout_in_seconds(self, timeout_in_seconds: int):
        """
        Setter for timeout_in_seconds.
        """
        if timeout_in_seconds <= 0:
            message = "The property 'timeout_in_seconds' must be greater than zero."
            get_logger().log_info(message)
            raise ValueError(message)
        self.timeout_in_seconds = timeout_in_seconds

    def get_timeout_in_seconds(self) -> int:
        """
        Getter for timeout_in_seconds.
        """
        return self.timeout_in_seconds

    def set_check_interval_in_seconds(self, check_interval_in_seconds: int):
        """
        Setter for check_interval_in_seconds.
        """
        if check_interval_in_seconds <= 0:
            message = "The property 'check_interval_in_seconds' must be greater than zero."
            get_logger().log_info(message)
            raise ValueError(message)
        self.check_interval_in_seconds = check_interval_in_seconds

    def get_check_interval_in_seconds(self) -> int:
        """
        Getter for check_interval_in_seconds.
        """
        return self.check_interval_in_seconds

    def set_expected_status(self, expected_status: SystemApplicationStatusEnum):
        """
        Setter for expected_status.
        """
        if expected_status not in SystemApplicationStatusEnum:
            message = "The property 'expected_status' must be specified with a valid value."
            get_logger().log_info(message)
            raise ValueError(message)
        self.expected_status = expected_status

    def get_expected_status(self) -> SystemApplicationStatusEnum:
        """
        Getter for expected_status.
        """
        return self.expected_status

    def set_app_name(self, app_name: str):
        """
        Setter for app_name.
        """
        if String.is_empty(app_name):
            message = "The property 'app_name' must be specified."
            get_logger().log_info(message)
            raise ValueError(message)
        self.app_name = app_name

    def get_app_name(self) -> str:
        """
        Getter for app_name.
        """
        return self.app_name
