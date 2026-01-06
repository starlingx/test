from typing import Any, Dict


class ParentDataSet:
    """
    Class models a parent data set
    """

    def __init__(self, expected_dict: Dict[str, Any]):
        """
        Constructor.

        Args:
            expected_dict (Dict[str, Any]): The dictionary read from the JSON setup template file associated with this parent data set
        """
        if not isinstance(expected_dict, dict):
            raise Exception(f"Expected a dictionary for parent_data_set but received: {type(expected_dict).__name__} with value: {expected_dict}. This may indicate an unresolved template variable.")

        if "gm_clock_class" not in expected_dict:
            raise Exception("Every expected dict should have a gm_clock_class.")
        gm_clock_class = expected_dict["gm_clock_class"]
        self.gm_clock_class = gm_clock_class if isinstance(gm_clock_class, list) else [gm_clock_class]

        if "gm_clock_accuracy" not in expected_dict:
            raise Exception("Every expected dict should have a gm_clock_accuracy.")
        self.gm_clock_accuracy = expected_dict["gm_clock_accuracy"]

        if "gm_offset_scaled_log_variance" not in expected_dict:
            raise Exception("Every expected dict should have a gm_offset_scaled_log_variance.")
        self.gm_offset_scaled_log_variance = expected_dict["gm_offset_scaled_log_variance"]

    def get_gm_clock_class(self) -> list:
        """
        Gets the gm clock class.

        Returns:
            list: The gm clock class.
        """
        return self.gm_clock_class

    def get_gm_clock_accuracy(self) -> str:
        """
        Gets the gm clock accuracy.

        Returns:
            str: The gm clock accuracy.
        """
        return self.gm_clock_accuracy

    def get_gm_offset_scaled_log_variance(self) -> str:
        """
        Gets the gm offset scaled log variance.

        Returns:
            str: The gm offset scaled log variance.
        """
        return self.gm_offset_scaled_log_variance
