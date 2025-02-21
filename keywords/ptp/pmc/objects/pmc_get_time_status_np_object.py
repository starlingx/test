class PMCGetTimeStatusNpObject:
    """
    Object to hold the values of TIME_STATUS_NP
    """

    def __init__(self):
        self.master_offset = -1
        self.ingress_time = -1
        self.cumulative_scaled_rate_offset = ''
        self.scaled_last_gm_phase_change = -1
        self.gm_time_base_indicator = -1
        self.last_gm_phase_change = ''
        self.gm_present = ''
        self.gm_identity = ''
    
    def get_master_offset(self) -> int:
        """Getter for master offset

        Returns: the master offset
        """
        return self.master_offset

    def set_master_offset(self, master_offset : int):
        """Setter for master offset

        Args:
            master_offset : the master offset value
        """
        self.master_offset = master_offset

    def get_ingress_time(self) -> int:
        """Getter for ingress time

        Returns: the ingress time
        """
        return self.ingress_time

    def set_ingress_time(self, ingress_time : int):
        """Setter for ingress time

        Args:
            ingress_time : the ingress time value
        """
        self.ingress_time = ingress_time

    def get_cumulative_scaled_rate_offset(self) -> str:
        """Getter for cumulative scaled rate offset

        Returns: the cumulative scaled rate offset
        """
        return self.cumulative_scaled_rate_offset

    def set_cumulative_scaled_rate_offset(self, cumulative_scaled_rate_offset : str):
        """Setter for cumulative scaled rate offset

        Args:
            cumulative_scaled_rate_offset : the cumulative scaled rate offset value
        """
        self.cumulative_scaled_rate_offset = cumulative_scaled_rate_offset

    def get_scaled_last_gm_phase_change(self) -> int:
        """Getter for scaled last GM phase change

        Returns: the scaled last GM phase change
        """
        return self.scaled_last_gm_phase_change

    def set_scaled_last_gm_phase_change(self, scaled_last_gm_phase_change : int):
        """Setter for scaled last GM phase change

        Args:
            scaled_last_gm_phase_change : the scaled last GM phase change value
        """
        self.scaled_last_gm_phase_change = scaled_last_gm_phase_change

    def get_gm_time_base_indicator(self) -> int:
        """Getter for GM time base indicator

        Returns: the GM time base indicator value
        """
        return self.gm_time_base_indicator

    def set_gm_time_base_indicator(self, gm_time_base_indicator : int):
        """Setter for GM time base indicator

        Args: 
            gm_time_base_indicator : the GM time base indicator value
        """
        self.gm_time_base_indicator = gm_time_base_indicator

    def get_last_gm_phase_change(self) -> str:
        """Getter for last GM phase change

        Returns: the last GM phase change value
        """
        return self.last_gm_phase_change

    def set_last_gm_phase_change(self, last_gm_phase_change : str):
        """Setter for last GM phase change

        Args:
            last_gm_phase_change : the last GM phase change value
        """
        self.last_gm_phase_change = last_gm_phase_change

    def get_gm_present(self) -> str:
        """Getter for GM presence

        Returns: the GM present
       """
        return self.gm_present

    def set_gm_present(self, gm_present : str):
        """Setter for GM presence.

        Args:
            gm_present: the GM present value
        """
        self.gm_present = gm_present

    def get_gm_identity(self) -> str:
        """Getter for GM identity

        Returns: the GM identity
        """
        return self.gm_identity

    def set_gm_identity(self, gm_identity : str):
        """Setter for GM identity.

        Args:
            gm_identity: the GM identity value
        """
        self.gm_identity = gm_identity