from typing import Any, Dict


class TimePropertiesDataSet:
    """
    Class models a time properties data set
    """

    def __init__(self, expected_dict: Dict[str, Any]):
        """
        Constructor.

        Args:
            expected_dict (Dict[str, Any]): The dictionary read from the JSON setup template file associated with this time properties data set

        """
        if "current_utc_offset" not in expected_dict:
            raise Exception("Every expected dict should have a current_utc_offset.")
        self.current_utc_offset = expected_dict["current_utc_offset"]

        if "current_utc_offset_valid" not in expected_dict:
            raise Exception("Every expected dict should have a current_utc_offset_valid.")
        self.current_utc_offset_valid = expected_dict["current_utc_offset_valid"]

        if "time_traceable" not in expected_dict:
            raise Exception("Every expected dict should have a time_traceable.")
        self.time_traceable = expected_dict["time_traceable"]

        if "frequency_traceable" not in expected_dict:
            raise Exception("Every expected dict should have a frequency_traceable.")
        self.frequency_traceable = expected_dict["frequency_traceable"]

    def get_current_utc_offset(self) -> int:
        """
        Gets the current UTC offset.

        Returns:
            int: The current UTC offset.
        """
        return self.current_utc_offset

    def get_current_utc_offset_valid(self) -> int:
        """
        Gets the validity of the current UTC offset.

        Returns:
            int: The offset scaled log variance.
        """
        return self.current_utc_offset_valid

    def get_time_traceable(self) -> int:
        """
        Gets the time traceability.

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
