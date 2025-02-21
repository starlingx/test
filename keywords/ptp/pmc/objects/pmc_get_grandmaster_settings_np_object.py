class PMCGetGrandmasterSettingsNpObject:
    """
    Object to hold the values of GRANDMASTER_SETTINGS_NP
    """

    def __init__(self):
        self.clock_class: int = -1
        self.clock_accuracy: str = ''
        self.offset_scaled_log_variance: str = ''
        self.current_utc_offset: int = -1
        self.leap61: int = -1
        self.leap59: int = -1
        self.current_utc_off_set_valid: int = -1
        self.ptp_time_scale: int = -1
        self.time_traceable: int = -1
        self.frequency_traceable: int = -1
        self.time_source: str = ''         

    def get_clock_class(self) -> int:
        """
        Getter for clock_class
        Returns: the clock_class value

        """
        return self.clock_class

    def set_clock_class(self, clock_class: int):
        """
        Setter for clock_class
        Args:
            clock_class : the clock_class value

        Returns:

        """
        self.clock_class = clock_class

    def get_clock_accuracy(self) -> str:
        """
        Getter for clock_accuracy
        Returns: the clock_accuracy value

        """
        return self.clock_accuracy

    def set_clock_accuracy(self, clock_accuracy: str):
        """
        Setter for clock_accuracy
        Args:
            clock_accuracy : the clock_accuracy value

        Returns:

        """
        self.clock_accuracy = clock_accuracy

    def get_offset_scaled_log_variance(self) -> str:
        """
        Getter for offset_scaled_log_variance
        Returns: the offset_scaled_log_variance value

        """
        return self.offset_scaled_log_variance

    def set_offset_scaled_log_variance(self, offset_scaled_log_variance: str):
        """
        Setter for offset_scaled_log_variance
        Args:
            offset_scaled_log_variance : the offset_scaled_log_variance value

        Returns:

        """
        self.offset_scaled_log_variance = offset_scaled_log_variance

    def get_current_utc_offset(self) -> int:
        """
        Getter for current_utc_offset
        Returns: the current_utc_offset value

        """
        return self.current_utc_offset

    def set_current_utc_offset(self, current_utc_offset: int):
        """
        Setter for current_utc_offset
        Args:
            current_utc_offset : the current_utc_offset value

        Returns:

        """
        self.current_utc_offset = current_utc_offset
    
    def get_leap61(self) -> int:
        """
        Getter for leap61
        Returns: the leap61 value

        """
        return self.leap61

    def set_leap61(self, leap61: int):
        """
        Setter for leap61
        Args:
            leap61 : the leap61 value

        Returns:

        """
        self.leap61 = leap61
    
    def get_leap59(self) -> int:
        """
        Getter for leap59
        Returns: the leap59 value

        """
        return self.leap59

    def set_leap59(self, leap59: int):
        """
        Setter for leap59
        Args:
            leap59 : the leap59 value

        Returns:

        """
        self.leap59 = leap59
    
    def get_current_utc_off_set_valid(self) -> int:
        """
        Getter for current_utc_off_set_valid
        Returns: the current_utc_off_set_valid value

        """
        return self.current_utc_off_set_valid

    def set_current_utc_off_set_valid(self, current_utc_off_set_valid: int):
        """
        Setter for current_utc_off_set_valid
        Args:
            current_utc_off_set_valid : the current_utc_off_set_valid value

        Returns:

        """
        self.current_utc_off_set_valid = current_utc_off_set_valid
    
    def get_ptp_time_scale(self) -> int:
        """
        Getter for ptp_time_scale
        Returns: the ptp_time_scale value

        """
        return self.ptp_time_scale

    def set_ptp_time_scale(self, ptp_time_scale: int):
        """
        Setter for ptp_time_scale
        Args:
            ptp_time_scale : the ptp_time_scale value

        Returns:

        """
        self.ptp_time_scale = ptp_time_scale

    def get_time_traceable(self) -> int:
        """
        Getter for time_traceable
        Returns: the time_traceable value

        """
        return self.time_traceable

    def set_time_traceable(self, time_traceable: int):
        """
        Setter for time_traceable
        Args:
            time_traceable : the time_traceable value

        Returns:

        """
        self.time_traceable = time_traceable

    def get_frequency_traceable(self) -> int:
        """
        Getter for frequency_traceable
        Returns: the frequency_traceable value

        """
        return self.frequency_traceable

    def set_frequency_traceable(self, frequency_traceable: int):
        """
        Setter for frequency_traceable
        Args:
            frequency_traceable : the frequency_traceable value

        Returns:

        """
        self.frequency_traceable = frequency_traceable

    def get_time_source(self) -> str:
        """
        Getter for time_source
        Returns: the time_source value

        """
        return self.time_source

    def set_time_source(self, time_source: str):
        """
        Setter for time_source
        Args:
            time_source : the time_source value

        Returns:

        """
        self.time_source = time_source    



