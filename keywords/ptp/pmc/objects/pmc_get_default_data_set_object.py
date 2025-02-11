class PMCGetDefaultDataSetObject:
    """
    Object to hold the values of default data set
    """

    def __init__(self):
        self.two_step_flag: int = -1
        self.slave_only: int = -1
        self.number_ports: int = -1
        self.socket_priority: int = -1
        self.priority1: int = -1
        self.clock_class: int = -1
        self.clock_accuracy: str = ''
        self.offset_scaled_log_variance: str = ''
        self.priority2: int = -1
        self.clock_identity: str = ''
        self.domain_number: str = ''
        self.free_running: int = -1
        self.freq_est_interval: int = -1
        self.dscp_event: int = -1
        self.dscp_general: int = -1
        self.dataset_comparison: str = ''
        self.max_steps_removed: int = -1
        self.utc_offset: int = -1

    def get_two_step_flag(self) -> int:
        """
        Getter for two_step_flag
        Returns: two_step_flag

        """
        return self.two_step_flag

    def set_two_step_flag(self, two_step_flag: int):
        """
        Setter for two_step_flag
        Args:
            two_step_flag (): the two_step_flag value

        Returns:

        """
        self.two_step_flag = two_step_flag

    def get_slave_only(self) -> int:
        """
        Getter for slave_only
        Returns: slave_only value

        """
        return self.slave_only

    def set_slave_only(self, slave_only: int):
        """
        Setter for slave_only
        Args:
            slave_only (): slave_only value

        Returns:

        """
        self.slave_only = slave_only

    def get_socket_priority(self) -> int:
        """
        Getter for socket_priority
        Returns: socket_priority value

        """
        return self.socket_priority

    def set_socket_priority(self, socket_priority: int):
        """
        Setter for socket_priority
        Args:
            socket_priority (): socket_priority value

        Returns:

        """
        self.socket_priority = socket_priority

    def get_number_ports(self) -> int:
        """
        Getter for number_ports
        Returns: the number_ports value

        """
        return self.number_ports

    def set_number_ports(self, number_ports: int):
        """
        Setter for number_ports
        Args:
            number_ports (): the number_ports value

        Returns:

        """
        self.number_ports = number_ports

    def get_priority1(self) -> int:
        """
        Getter for priority1
        Returns: priority1 value

        """
        return self.priority1

    def set_priority1(self, priority1: int):
        """
        Setter for priority1
        Args:
            priority1 (): the priority1 value

        Returns:

        """
        self.priority1 = priority1

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
            clock_class (): the clock_class value

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
            clock_accuracy (): the clock_accuracy value

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
            offset_scaled_log_variance (): the offset_scaled_log_variance value

        Returns:

        """
        self.offset_scaled_log_variance = offset_scaled_log_variance

    def get_priority2(self) -> int:
        """
        Getter for priority2
        Returns: the priority2 value

        """
        return self.priority2

    def set_priority2(self, priority2: int):
        """
        Setter for priority2
        Args:
            priority2 (): the priority2 value

        Returns:

        """
        self.priority2 = priority2

    def get_clock_identity(self) -> str:
        """
        Getter for clock_identity
        Returns: the clock_identity value

        """
        return self.clock_identity

    def set_clock_identity(self, clock_identity: str):
        """
        Setter for clock_identity
        Args:
            clock_identity (): the clock_identity value

        Returns:

        """
        self.clock_identity = clock_identity

    def get_domain_number(self) -> str:
        """
        Getter for domain_number
        Returns: the domain_number value

        """
        return self.domain_number

    def set_domain_number(self, domain_number: str):
        """
        Setter for domain_number
        Args:
            domain_number (): the domain_number value

        Returns:

        """
        self.domain_number = domain_number

    def get_free_running(self) -> int:
        """
        Getter for free_running
        Returns: the free_running value

        """
        return self.free_running

    def set_free_running(self, free_running: int):
        """
        Setter for free_running
        Args:
            free_running (): the free_running value

        Returns:

        """
        self.free_running = free_running

    def get_freq_est_interval(self) -> int:
        """
        Getter for freq_est_interval
        Returns: the freq_est_interval value

        """
        return self.freq_est_interval

    def set_freq_est_interval(self, freq_est_interval: int):
        """
        Setter for freq_est_interval
        Args:
            freq_est_interval (): the freq_est_interval value

        Returns:

        """
        self.freq_est_interval = freq_est_interval

    def get_dscp_event(self) -> int:
        """
        Getter for dscp_event
        Returns: the dscp_event value

        """
        return self.dscp_event

    def set_dscp_event(self, dscp_event: int):
        """
        Setter for dscp_event
        Args:
            dscp_event (): the dscp_event value

        Returns:

        """
        self.dscp_event = dscp_event

    def get_dscp_event(self) -> int:
        """
        Getter for priority2
        Returns: the priority2 value

        """
        return self.dscp_event

    def set_dscp_event(self, dscp_event: int):
        """
        Setter for dscp_event
        Args:
            dscp_event (): the dscp_event value

        Returns:

        """
        self.dscp_event = dscp_event

    def get_dscp_general(self) -> int:
        """
        Getter for dscp_general
        Returns: the dscp_general value

        """
        return self.dscp_general

    def set_dscp_general(self, dscp_general: int):
        """
        Setter for dscp_general
        Args:
            dscp_general (): the dscp_general value

        Returns:

        """
        self.dscp_general = dscp_general

    def get_dataset_comparison(self) -> str:
        """
        Getter for dataset_comparison
        Returns: the dataset_comparison value

        """
        return self.dataset_comparison

    def set_dataset_comparison(self, dataset_comparison: str):
        """
        Setter for dataset_comparison
        Args:
            dataset_comparison (): the dataset_comparison value

        Returns:

        """
        self.dataset_comparison = dataset_comparison

    def get_max_steps_removed(self) -> int:
        """
        Getter for max_steps_removed
        Returns: the max_steps_removed value

        """
        return self.max_steps_removed

    def set_max_steps_removed(self, max_steps_removed: int):
        """
        Setter for max_steps_removed
        Args:
            max_steps_removed (): the max_steps_removed value

        Returns:

        """
        self.max_steps_removed = max_steps_removed

    def get_utc_offset(self) -> int:
        """
        Getter for utc_offset
        Returns: the utc_offset value

        """
        return self.utc_offset

    def set_utc_offset(self, utc_offset: int):
        """
        Setter for utc_offset
        Args:
            utc_offset (): the utc_offset value

        Returns:

        """
        self.utc_offset = utc_offset



