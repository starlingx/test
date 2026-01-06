from typing import Any, Dict


class GrandmasterSettings:
    """
    Class models a grandmaster settings
    """

    def __init__(self, expected_dict: Dict[str, Any]):
        """
        Constructor.

        Args:
            expected_dict (Dict[str, Any]): The dictionary read from the JSON setup template file associated with this grandmaster settings

        """
        if "clock_class" not in expected_dict:
            raise Exception("Every expected dict should have a clock_class.")
        clock_class = expected_dict["clock_class"]
        self.clock_class = clock_class if isinstance(clock_class, list) else [clock_class]

        if "clock_accuracy" not in expected_dict:
            raise Exception("Every expected dict should have a clock_accuracy.")
        self.clock_accuracy = expected_dict["clock_accuracy"]

        if "offset_scaled_log_variance" not in expected_dict:
            raise Exception("Every expected dict should have a offset_scaled_log_variance.")
        self.offset_scaled_log_variance = expected_dict["offset_scaled_log_variance"]

        if "time_traceable" not in expected_dict:
            raise Exception("Every expected dict should have a time_traceable.")
        self.time_traceable = expected_dict["time_traceable"]

        if "frequency_traceable" not in expected_dict:
            raise Exception("Every expected dict should have a frequency_traceable.")
        self.frequency_traceable = expected_dict["frequency_traceable"]

        if "time_source" not in expected_dict:
            raise Exception("Every expected dict should have a time_source.")
        self.time_source = expected_dict["time_source"]

        if "current_utc_offset_valid" not in expected_dict:
            raise Exception("Every expected dict should have a current_utc_offset_valid.")
        self.current_utc_offset_valid = expected_dict["current_utc_offset_valid"]

    def get_clock_class(self) -> list:
        """
        Gets the clock class.

        Returns:
            list: The clock class.
        """
        return self.clock_class

    def get_clock_accuracy(self) -> str:
        """
        Gets the clock accuracy

        Returns:
            str: The clock accuracy.
        """
        return self.clock_accuracy

    def get_offset_scaled_log_variance(self) -> str:
        """
        Gets the offset scaled log variance.

        Returns:
            str: The offset scaled log variance.
        """
        return self.offset_scaled_log_variance

    def get_time_traceable(self) -> int:
        """
        Gets the time traceability

        Returns:
            int: The time traceability.
        """
        return self.time_traceable

    def get_frequency_traceable(self) -> int:
        """
        Gets the frequency traceability.

        Returns:
            int: The frequency traceability.
        """
        return self.frequency_traceable

    def get_time_source(self) -> str:
        """
        Gets the time source.

        Returns:
            str: The time source.
        """
        return self.time_source

    def get_current_utc_offset_valid(self) -> int:
        """
        Gets the validity of the UTC offset.

        Returns:
            int: The current utc offset valid.
        """
        return self.current_utc_offset_valid
