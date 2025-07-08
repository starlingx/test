class PMCGetParentDataSetObject:
    """
    Object to hold attributes of Parent set object
    """

    def __init__(self):
        self.parent_port_identity: str = ""
        self.parent_stats: int = -1
        self.observed_parent_offset_scaled_log_variance: str = ""
        self.observed_parent_clock_phase_change_rate: str = ""
        self.grandmaster_priority1: int = -1
        self.gm_clock_class: int = -1
        self.gm_clock_accuracy: str = ""
        self.gm_offset_scaled_log_variance: str = ""
        self.grandmaster_priority2: int = -1
        self.grandmaster_identity: str = ""

    def get_parent_port_identity(self) -> str:
        """
        Getter for parent_port_identity

        Returns:
            str: parent_port_identity
        """
        return self.parent_port_identity

    def set_parent_port_identity(self, parent_port_identity: str) -> None:
        """
        Setter for parent_port_identity

        Args:
            parent_port_identity (str): the parent_port_identity value

        Returns:
            None: This method does not return anything.
        """
        self.parent_port_identity = parent_port_identity

    def get_parent_stats(self) -> int:
        """
        Getter for parent_stats

        Returns:
            int: parent_stats value

        """
        return self.parent_stats

    def set_parent_stats(self, parent_stats: int) -> None:
        """
        Setter for parent_stats

        Args:
            parent_stats (int): parent_stats value

        Returns:
            None: This method does not return anything.
        """
        self.parent_stats = parent_stats

    def get_observed_parent_offset_scaled_log_variance(self) -> str:
        """
        Getter for observed_parent_offset_scaled_log_variance

        Returns:
            str: the observed_parent_offset_scaled_log_variance value
        """
        return self.observed_parent_offset_scaled_log_variance

    def set_observed_parent_offset_scaled_log_variance(self, observed_parent_offset_scaled_log_variance: str) -> None:
        """
        Setter for observed_parent_offset_scaled_log_variance

        Args:
            observed_parent_offset_scaled_log_variance (str): the observed_parent_offset_scaled_log_variance value

        Returns:
            None: This method does not return anything.
        """
        self.observed_parent_offset_scaled_log_variance = observed_parent_offset_scaled_log_variance

    def get_observed_parent_clock_phase_change_rate(self) -> str:
        """
        Getter for observed_parent_clock_phase_change_rate

        Returns:
            str: observed_parent_clock_phase_change_rate value
        """
        return self.observed_parent_clock_phase_change_rate

    def set_observed_parent_clock_phase_change_rate(self, observed_parent_clock_phase_change_rate: str) -> None:
        """
        Setter for observed_parent_clock_phase_change_rate

        Args:
            observed_parent_clock_phase_change_rate (str): the observed_parent_clock_phase_change_rate value

        Returns:
            None: This method does not return anything.
        """
        self.observed_parent_clock_phase_change_rate = observed_parent_clock_phase_change_rate

    def get_grandmaster_priority1(self) -> int:
        """
        Getter for grandmaster_priority1

        Returns:
            int: the grandmaster_priority1 value
        """
        return self.grandmaster_priority1

    def set_grandmaster_priority1(self, grandmaster_priority1: int) -> None:
        """
        Setter for grandmaster_priority1

        Args:
            grandmaster_priority1 (int): the grandmaster_priority1 value

        Returns:
            None: This method does not return anything.
        """
        self.grandmaster_priority1 = grandmaster_priority1

    def get_gm_clock_class(self) -> int:
        """
        Getter for gm_clock_class

        Returns:
            int: the gm_clock_class value
        """
        return self.gm_clock_class

    def set_gm_clock_class(self, gm_clock_class: int) -> None:
        """
        Setter for gm_clock_class

        Args:
            gm_clock_class (int): the gm_clock_class value

        Returns:
            None: This method does not return anything.
        """
        self.gm_clock_class = gm_clock_class

    def get_gm_clock_accuracy(self) -> str:
        """
        Getter for gm_clock_accuracy

        Returns:
            str: the gm_clock_accuracy value
        """
        return self.gm_clock_accuracy

    def set_gm_clock_accuracy(self, gm_clock_accuracy: str) -> None:
        """
        Setter for gm_clock_accuracy

        Args:
            gm_clock_accuracy (str): the gm_clock_accuracy value

        Returns:
            None: This method does not return anything.
        """
        self.gm_clock_accuracy = gm_clock_accuracy

    def get_gm_offset_scaled_log_variance(self) -> str:
        """
        Getter for gm_offset_scaled_log_variance

        Returns:
            str: the gm_offset_scaled_log_variance value
        """
        return self.gm_offset_scaled_log_variance

    def set_gm_offset_scaled_log_variance(self, gm_offset_scaled_log_variance: str) -> None:
        """
        Setter for gm_offset_scaled_log_variance

        Args:
            gm_offset_scaled_log_variance (str): the gm_offset_scaled_log_variance value

        Returns:
            None: This method does not return anything.
        """
        self.gm_offset_scaled_log_variance = gm_offset_scaled_log_variance

    def get_grandmaster_priority2(self) -> int:
        """
        Getter for grandmaster_priority2

        Returns:
                int: the grandmaster_priority2 value
        """
        return self.grandmaster_priority2

    def set_grandmaster_priority2(self, grandmaster_priority2: int) -> None:
        """
        Setter for grandmaster_priority2

        Args:
            grandmaster_priority2 (int): the grandmaster_priority2 value

        Returns:
            None: This method does not return anything.
        """
        self.grandmaster_priority2 = grandmaster_priority2

    def get_grandmaster_identity(self) -> str:
        """
        Getter for grandmaster_identity

        Returns:
            str: the grandmaster_identity value
        """
        return self.grandmaster_identity

    def set_grandmaster_identity(self, grandmaster_identity: str) -> None:
        """
        Setter for grandmaster_identity

        Args:
            grandmaster_identity (str): the grandmaster_identity value

        Returns:
            None: This method does not return anything.history
        """
        self.grandmaster_identity = grandmaster_identity
