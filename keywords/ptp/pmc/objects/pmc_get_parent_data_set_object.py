class PMCGetParentDataSetObject:
    """
    Object to hold attributes of Parent set object
    """

    def __init__(self):
        self.parent_port_identity: str = ''
        self.parent_stats: int = -1
        self.observed_parent_offset_scaled_log_variance: str = ''
        self.observed_parent_clock_phase_change_rate: str = ''
        self.grandmaster_priority1: int = -1
        self.gm_clock_class: int = -1
        self.gm_clock_accuracy: str = ''
        self.gm_offset_scaled_log_variance: str = ''
        self.grandmaster_priority2: int = -1
        self.grandmaster_identity: str = ''

    def get_parent_port_identity(self) -> str:
        """
        Getter for parent_port_identity
        Returns: parent_port_identity

        """
        return self.parent_port_identity

    def set_parent_port_identity(self, parent_port_identity: str):
        """
        Setter for parent_port_identity
        Args:
            parent_port_identity (): the parent_port_identity value

        Returns:

        """
        self.parent_port_identity = parent_port_identity

    def get_parent_stats(self) -> int:
        """
        Getter for parent_stats
        Returns: parent_stats value

        """
        return self.parent_stats

    def set_parent_stats(self, parent_stats: int):
        """
        Setter for parent_stats
        Args:
            parent_stats (): parent_stats value

        Returns:

        """
        self.parent_stats = parent_stats

    def get_observed_parent_offset_scaled_log_variance(self) -> str:
        """
        Getter for observed_parent_offset_scaled_log_variance
        Returns: the observed_parent_offset_scaled_log_variance value

        """
        return self.observed_parent_offset_scaled_log_variance

    def set_observed_parent_offset_scaled_log_variance(self, observed_parent_offset_scaled_log_variance: str):
        """
        Setter for observed_parent_offset_scaled_log_variance
        Args:
            observed_parent_offset_scaled_log_variance (): the observed_parent_offset_scaled_log_variance value

        Returns:

        """
        self.observed_parent_offset_scaled_log_variance = observed_parent_offset_scaled_log_variance

    def get_observed_parent_clock_phase_change_rate(self) -> str:
        """
        Getter for observed_parent_clock_phase_change_rate
        Returns: observed_parent_clock_phase_change_rate value

        """
        return self.observed_parent_clock_phase_change_rate

    def set_observed_parent_clock_phase_change_rate(self, observed_parent_clock_phase_change_rate: str):
        """
        Setter for observed_parent_clock_phase_change_rate
        Args:
            observed_parent_clock_phase_change_rate (): the observed_parent_clock_phase_change_rate value

        Returns:

        """
        self.observed_parent_clock_phase_change_rate = observed_parent_clock_phase_change_rate

    def get_grandmaster_priority1(self) -> int:
        """
        Getter for grandmaster_priority1
        Returns: the grandmaster_priority1 value

        """
        return self.grandmaster_priority1

    def set_grandmaster_priority1(self, grandmaster_priority1: int):
        """
        Setter for grandmaster_priority1
        Args:
            grandmaster_priority1 (): the grandmaster_priority1 value

        Returns:

        """
        self.grandmaster_priority1 = grandmaster_priority1

    def get_gm_clock_class(self) -> int:
        """
        Getter for gm_clock_class
        Returns: the gm_clock_class value

        """
        return self.gm_clock_class

    def set_gm_clock_class(self, gm_clock_class: int):
        """
        Setter for gm_clock_class
        Args:
            gm_clock_class (): the gm_clock_class value

        Returns:

        """
        self.gm_clock_class = gm_clock_class

    def get_gm_clock_accuracy(self) -> str:
        """
        Getter for gm_clock_accuracy
        Returns: the gm_clock_accuracy value

        """
        return self.gm_clock_accuracy

    def set_gm_clock_accuracy(self, gm_clock_accuracy: str):
        """
        Setter for gm_clock_accuracy
        Args:
            gm_clock_accuracy (): the gm_clock_accuracy value

        Returns:

        """
        self.gm_clock_accuracy = gm_clock_accuracy

    def get_gm_offset_scaled_log_variance(self) -> str:
        """
        Getter for gm_offset_scaled_log_variance
        Returns: the gm_offset_scaled_log_variance value

        """
        return self.gm_offset_scaled_log_variance

    def set_gm_offset_scaled_log_variance(self, gm_offset_scaled_log_variance: str):
        """
        Setter for gm_offset_scaled_log_variance
        Args:
            gm_offset_scaled_log_variance (): the gm_offset_scaled_log_variance value

        Returns:

        """
        self.gm_offset_scaled_log_variance = gm_offset_scaled_log_variance

    def get_grandmaster_priority2(self) -> int:
        """
        Getter for grandmaster_priority2
        Returns: the grandmaster_priority2 value

        """
        return self.grandmaster_priority2

    def set_grandmaster_priority2(self, grandmaster_priority2: int):
        """
        Setter for grandmaster_priority2
        Args:
            grandmaster_priority2 (): the grandmaster_priority2 value

        Returns:

        """
        self.grandmaster_priority2 = grandmaster_priority2

    def get_grandmaster_identity(self) -> str:
        """
        Getter for grandmaster_identity
        Returns: the grandmaster_identity value

        """
        return self.grandmaster_identity

    def set_grandmaster_identity(self, grandmaster_identity: str):
        """
        Setter for grandmaster_identity
        Args:
            grandmaster_identity (): the grandmaster_identity value

        Returns:

        """
        self.grandmaster_identity = grandmaster_identity
