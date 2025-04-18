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
        self.clock_accuracy: str = ""
        self.offset_scaled_log_variance: str = ""
        self.priority2: int = -1
        self.clock_identity: str = ""
        self.domain_number: str = ""
        self.free_running: int = -1
        self.freq_est_interval: int = -1
        self.dscp_event: int = -1
        self.dscp_general: int = -1
        self.dataset_comparison: str = ""
        self.max_steps_removed: int = -1
        self.utc_offset: int = -1
        self.boundary_clock_jbod: int = -1
        self.clock_servo: str = ""
        self.delay_mechanism: str = ""
        self.message_tag: str = ""
        self.network_transport: str = ""
        self.summary_interval: int = -1
        self.time_stamping: str = ""
        self.tx_timestamp_timeout: int = -1
        self.uds_address: str = ""

    def get_two_step_flag(self) -> int:
        """
        Getter for two_step_flag

        Returns:
            int: two_step_flag

        """
        return self.two_step_flag

    def set_two_step_flag(self, two_step_flag: int):
        """
        Setter for two_step_flag

        Args:
            two_step_flag (int): the two_step_flag value

        """
        self.two_step_flag = two_step_flag

    def get_slave_only(self) -> int:
        """
        Getter for slave_only

        Returns:
            int: slave_only value

        """
        return self.slave_only

    def set_slave_only(self, slave_only: int):
        """
        Setter for slave_only

        Args:
            slave_only (int): slave_only value

        """
        self.slave_only = slave_only

    def get_socket_priority(self) -> int:
        """
        Getter for socket_priority

        Returns:
            int: socket_priority value

        """
        return self.socket_priority

    def set_socket_priority(self, socket_priority: int):
        """
        Setter for socket_priority

        Args:
            socket_priority (int): socket_priority value

        """
        self.socket_priority = socket_priority

    def get_number_ports(self) -> int:
        """
        Getter for number_ports

        Returns:
            int: the number_ports value

        """
        return self.number_ports

    def set_number_ports(self, number_ports: int):
        """
        Setter for number_ports

        Args:
            number_ports (int): the number_ports value

        """
        self.number_ports = number_ports

    def get_priority1(self) -> int:
        """
        Getter for priority1

        Returns:
            int: priority1 value

        """
        return self.priority1

    def set_priority1(self, priority1: int):
        """
        Setter for priority1

        Args:
            priority1 (int): the priority1 value

        """
        self.priority1 = priority1

    def get_clock_class(self) -> int:
        """
        Getter for clock_class

        Returns:
            int: the clock_class value

        """
        return self.clock_class

    def set_clock_class(self, clock_class: int):
        """
        Setter for clock_class

        Args:
            clock_class (int): the clock_class value

        """
        self.clock_class = clock_class

    def get_clock_accuracy(self) -> str:
        """
        Getter for clock_accuracy

        Returns:
            str: the clock_accuracy value

        """
        return self.clock_accuracy

    def set_clock_accuracy(self, clock_accuracy: str):
        """
        Setter for clock_accuracy

        Args:
            clock_accuracy (str): the clock_accuracy value

        """
        self.clock_accuracy = clock_accuracy

    def get_offset_scaled_log_variance(self) -> str:
        """
        Getter for offset_scaled_log_variance

        Returns:
            str: the offset_scaled_log_variance value

        """
        return self.offset_scaled_log_variance

    def set_offset_scaled_log_variance(self, offset_scaled_log_variance: str):
        """
        Setter for offset_scaled_log_variance

        Args:
            offset_scaled_log_variance (str): the offset_scaled_log_variance value

        """
        self.offset_scaled_log_variance = offset_scaled_log_variance

    def get_priority2(self) -> int:
        """
        Getter for priority2

        Returns:
            int: the priority2 value

        """
        return self.priority2

    def set_priority2(self, priority2: int):
        """
        Setter for priority2

        Args:
            priority2 (int): the priority2 value

        """
        self.priority2 = priority2

    def get_clock_identity(self) -> str:
        """
        Getter for clock_identity

        Returns:
            str: the clock_identity value

        """
        return self.clock_identity

    def set_clock_identity(self, clock_identity: str):
        """
        Setter for clock_identity

        Args:
            clock_identity (str): the clock_identity value

        """
        self.clock_identity = clock_identity

    def get_domain_number(self) -> int:
        """
        Getter for domain_number

        Returns:
            str: the domain_number value

        """
        return self.domain_number

    def set_domain_number(self, domain_number: int):
        """
        Setter for domain_number

        Args:
            domain_number (str): the domain_number value

        """
        self.domain_number = domain_number

    def get_free_running(self) -> int:
        """
        Getter for free_running

        Returns:
            int: the free_running value

        """
        return self.free_running

    def set_free_running(self, free_running: int):
        """
        Setter for free_running

        Args:
            free_running (int): the free_running value

        """
        self.free_running = free_running

    def get_freq_est_interval(self) -> int:
        """
        Getter for freq_est_interval

        Returns:
            int: the freq_est_interval value

        """
        return self.freq_est_interval

    def set_freq_est_interval(self, freq_est_interval: int):
        """
        Setter for freq_est_interval

        Args:
            freq_est_interval (int): the freq_est_interval value\

        """
        self.freq_est_interval = freq_est_interval

    def get_dscp_event(self) -> int:
        """
        Getter for dscp_event

        Returns:
            int: the dscp_event value

        """
        return self.dscp_event

    def set_dscp_event(self, dscp_event: int):
        """
        Setter for dscp_event

        Args:
            dscp_event (int): the dscp_event value

        """
        self.dscp_event = dscp_event

    def get_dscp_general(self) -> int:
        """
        Getter for dscp_general

        Returns:
            int: the dscp_general value

        """
        return self.dscp_general

    def set_dscp_general(self, dscp_general: int):
        """
        Setter for dscp_general

        Args:
            dscp_general (int): the dscp_general value

        """
        self.dscp_general = dscp_general

    def get_dataset_comparison(self) -> str:
        """
        Getter for dataset_comparison

        Returns:
            str: the dataset_comparison value

        """
        return self.dataset_comparison

    def set_dataset_comparison(self, dataset_comparison: str):
        """
        Setter for dataset_comparison

        Args:
            dataset_comparison (str): the dataset_comparison value

        """
        self.dataset_comparison = dataset_comparison

    def get_max_steps_removed(self) -> int:
        """
        Getter for max_steps_removed

        Returns:
            int: the max_steps_removed value

        """
        return self.max_steps_removed

    def set_max_steps_removed(self, max_steps_removed: int):
        """
        Setter for max_steps_removed

        Args:
            max_steps_removed (int): the max_steps_removed value

        """
        self.max_steps_removed = max_steps_removed

    def get_utc_offset(self) -> int:
        """
        Getter for utc_offset

        Returns:
            int: the utc_offset value

        """
        return self.utc_offset

    def set_utc_offset(self, utc_offset: int):
        """
        Setter for utc_offset

        Args:
            utc_offset (int): the utc_offset value

        """
        self.utc_offset = utc_offset

    def set_boundary_clock_jbod(self, boundary_clock_jbod: int):
        """
        Setter for boundary_clock_jbod

        Args:
            boundary_clock_jbod (int): boundary_clock_jbod

        """
        self.boundary_clock_jbod = boundary_clock_jbod

    def get_boundary_clock_jbod(self) -> int:
        """
        Getter for boundary_clock_jbod

        Returns:
            int: the boundary_clock_jbod

        """
        return self.boundary_clock_jbod

    def set_clock_servo(self, clock_servo: str):
        """
        Setter for clock_servo

        Args:
            clock_servo (str): the clock_servo

        """
        self.clock_servo = clock_servo

    def get_clock_servo(self) -> str:
        """
        Getter for clock_servo

        Returns:
            str: the clock_servo

        """
        return self.clock_servo

    def set_delay_mechanism(self, delay_mechanism: str):
        """
        Setter for delay_mechanism

        Args:
            delay_mechanism (str): the delay_mechanism

        """
        self.delay_mechanism = delay_mechanism

    def get_delay_mechanism(self) -> str:
        """
        Getter for delay_mechanism

        Returns:
            str: the delay_mechanism
        """
        return self.delay_mechanism

    def set_message_tag(self, message_tag: str):
        """
        Setter for message_tag

        Args:
            message_tag (str): the message_tag

        """
        self.message_tag = message_tag

    def get_message_tag(self) -> str:
        """
        Getter for message_tag

        Returns:
            str: the message_tag

        """
        return self.message_tag

    def set_network_transport(self, network_transport: str):
        """
        Setter for network_transport

        Args:
            network_transport (str): the network_transport

        """
        self.network_transport = network_transport

    def get_network_transport(self) -> str:
        """
        Getter for network_transport

        Returns:
            str: the network_transport

        """
        return self.network_transport

    def set_summary_interval(self, summary_interval: int):
        """
        Setter for summary_interval

        Args:
            summary_interval (int): the summary_interval

        """
        self.summary_interval = summary_interval

    def get_summary_interval(self) -> int:
        """
        Getter for summary_interval

        Returns:
            int: the summary_interval

        """
        return self.summary_interval

    def set_time_stamping(self, time_stamping: str):
        """
        Setter for time_stamping

        Args:
            time_stamping (str): the time_stamping

        """
        self.time_stamping = time_stamping

    def get_time_stamping(self) -> str:
        """
        Getter for time_stamping

        Returns:
            str: the time_stamping

        """
        return self.time_stamping

    def set_tx_timestamp_timeout(self, tx_timestamp_timeout: int):
        """
        Setter for tx_timestamp_timeout

        Args:
            tx_timestamp_timeout (int): the tx_timestamp_timeout

        """
        self.tx_timestamp_timeout = tx_timestamp_timeout

    def get_tx_timestamp_timeout(self) -> int:
        """
        Getter for tx_timestamp_timeout

        Returns:
            int: the tx_timestamp_timeout

        """
        return self.tx_timestamp_timeout

    def set_uds_address(self, uds_address: str):
        """
        Setter for uds_address

        Args:
            uds_address (str): the uds_address

        """
        self.uds_address = uds_address

    def get_uds_address(self) -> str:
        """
        Getter for uds_address

        Returns:
            str: the uds_address

        """
        return self.uds_address
