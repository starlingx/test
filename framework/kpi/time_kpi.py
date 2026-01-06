import time

from framework.logging.automation_logger import get_logger


class TimeKPI:
    """
    A class to represent a time-based KPI (Key Performance Indicator).
    """

    def __init__(self, start_time: float):
        """Initialize the TimeKPI with a name and value.

        Args:
            start_time (float): The time when the KPI started.
        """
        self.start_time = start_time

    def log_elapsed_time(self, end_time: float, kpi_name: str) -> float:
        """Calculate the elapsed time since the start time.

        Args:
            end_time (float): The time when the KPI ended.
            kpi_name (str): The time when the KPI ended.

        Returns:
            float: The elapsed time.
        """
        elapsed_time = time.time() - self.start_time
        message = f"{kpi_name} elapsed time: {elapsed_time:.2f} seconds"
        get_logger().log_kpi(message)
