class PMCGetTimePropertiesDataSetObject:
    """
    Object to hold the values of TIME_PROPERTIES_DATA_SET
    """

    def __init__(self):
        self.current_utc_offset: int = -1
        self.leap61: int = -1
        self.leap59: int = -1
        self.current_utc_off_set_valid: int = -1
        self.ptp_time_scale: int = -1
        self.time_traceable: int = -1
        self.frequency_traceable: int = -1
        self.time_source: str = ""

    def get_current_utc_offset(self) -> int:
        """
        Getter for current_utc_offset

        Returns:
            int: the current_utc_offset value

        """
        return self.current_utc_offset

    def set_current_utc_offset(self, current_utc_offset: int) -> None:
        """
        Setter for current_utc_offset

        Args:
            current_utc_offset (int): the current_utc_offset value

        Returns:
            None: This method does not return anything.
        """
        self.current_utc_offset = current_utc_offset

    def get_leap61(self) -> int:
        """
        Getter for leap61

        Returns:
            int: the leap61 value

        """
        return self.leap61

    def set_leap61(self, leap61: int) -> None:
        """
        Setter for leap61

        Args:
            leap61 (int): the leap61 value

        Returns:
            None: This method does not return anything.
        """
        self.leap61 = leap61

    def get_leap59(self) -> int:
        """
        Getter for leap59

        Returns:
            int: the leap59 value

        """
        return self.leap59

    def set_leap59(self, leap59: int) -> None:
        """
        Setter for leap59

        Args:
            leap59 (int): the leap59 value

        Returns:
            None: This method does not return anything.
        """
        self.leap59 = leap59

    def get_current_utc_off_set_valid(self) -> int:
        """
        Getter for current_utc_off_set_valid

        Returns:
            int: the current_utc_off_set_valid value
        """
        return self.current_utc_off_set_valid

    def set_current_utc_off_set_valid(self, current_utc_off_set_valid: int) -> None:
        """
        Setter for current_utc_off_set_valid

        Args:
            current_utc_off_set_valid (int): the current_utc_off_set_valid value

        Returns:
            None: This method does not return anything.
        """
        self.current_utc_off_set_valid = current_utc_off_set_valid

    def get_ptp_time_scale(self) -> int:
        """
        Getter for ptp_time_scale

        Returns:
            int: the ptp_time_scale value
        """
        return self.ptp_time_scale

    def set_ptp_time_scale(self, ptp_time_scale: int) -> None:
        """
        Setter for ptp_time_scale

        Args:
            ptp_time_scale (int): the ptp_time_scale value

        Returns:
            None: This method does not return anything.
        """
        self.ptp_time_scale = ptp_time_scale

    def get_time_traceable(self) -> int:
        """
        Getter for time_traceable

        Returns:
            int: the time_traceable value
        """
        return self.time_traceable

    def set_time_traceable(self, time_traceable: int) -> None:
        """
        Setter for time_traceable

        Args:
            time_traceable (int): the time_traceable value

        Returns:
            None: This method does not return anything.

        """
        self.time_traceable = time_traceable

    def get_frequency_traceable(self) -> int:
        """
        Getter for frequency_traceable

        Returns:
            int: the frequency_traceable value
        """
        return self.frequency_traceable

    def set_frequency_traceable(self, frequency_traceable: int) -> None:
        """
        Setter for frequency_traceable

        Args:
            frequency_traceable (int): the frequency_traceable value

        Returns:
            None: This method does not return anything.

        """
        self.frequency_traceable = frequency_traceable

    def get_time_source(self) -> str:
        """
        Getter for time_source

        Returns:
            str: the time_source value
        """
        return self.time_source

    def set_time_source(self, time_source: str) -> None:
        """
        Setter for time_source

        Args:
            time_source (str): the time_source value

        Returns:
            None: This method does not return anything.
        """
        self.time_source = time_source
