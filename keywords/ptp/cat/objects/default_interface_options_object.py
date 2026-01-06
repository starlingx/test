class DefaultInterfaceOptionsObject:
    """
    Object to hold the values of Default Interface Options Object
    """

    def __init__(self):
        self.clock_type: str = ""
        self.network_transport: str = ""
        self.delay_mechanism: str = ""
        self.time_stamping: str = ""
        self.tsproc_mode: str = ""
        self.delay_filter: str = ""
        self.delay_filter_length: int = -1
        self.egress_latency: int = -1
        self.ingress_latency: int = -1
        self.boundary_clock_jbod: int = -1

    def get_clock_type(self) -> str:
        """
        Getter for clock_type

        Returns:
            str: the clock_type value
        """
        return self.clock_type

    def set_clock_type(self, clock_type: str) -> None:
        """
        Setter for clock_type

        Args:
            clock_type (str): the clock_type value
        """
        self.clock_type = clock_type

    def get_network_transport(self) -> str:
        """
        Getter for network_transport

        Returns:
            str: the network_transport value
        """
        return self.network_transport

    def set_network_transport(self, network_transport: str) -> None:
        """
        Setter for network_transport

        Args:
            network_transport (str): network_transport value
        """
        self.network_transport = network_transport

    def get_delay_mechanism(self) -> str:
        """
        Getter for delay_mechanism

        Returns:
            str: the delay_mechanism value
        """
        return self.delay_mechanism

    def set_delay_mechanism(self, delay_mechanism: str) -> None:
        """
        Setter for delay_mechanism

        Args:
            delay_mechanism (str): delay_mechanism value
        """
        self.delay_mechanism = delay_mechanism

    def get_time_stamping(self) -> str:
        """
        Getter for time_stamping

        Returns:
            str: the time_stamping value
        """
        return self.time_stamping

    def set_time_stamping(self, time_stamping: str) -> None:
        """
        Setter for time_stamping

        Args:
            time_stamping (str): the time_stamping value
        """
        self.time_stamping = time_stamping

    def get_tsproc_mode(self) -> str:
        """
        Getter for tsproc_mode

        Returns:
            str: the tsproc_mode value
        """
        return self.tsproc_mode

    def set_tsproc_mode(self, tsproc_mode: str) -> None:
        """
        Setter for tsproc_mode

        Args:
            tsproc_mode (str): the tsproc_mode value
        """
        self.tsproc_mode = tsproc_mode

    def get_delay_filter(self) -> str:
        """
        Getter for delay_filter

        Returns:
            str: the delay_filter value
        """
        return self.delay_filter

    def set_delay_filter(self, delay_filter: str) -> None:
        """
        Setter for delay_filter

        Args:
            delay_filter (str): the delay_filter value
        """
        self.delay_filter = delay_filter

    def get_delay_filter_length(self) -> int:
        """
        Getter for delay_filter_length

        Returns:
            int: the delay_filter_length value
        """
        return self.delay_filter_length

    def set_delay_filter_length(self, delay_filter_length: int) -> None:
        """
        Setter for delay_filter_length

        Args:
            delay_filter_length (int): the delay_filter_length value
        """
        self.delay_filter_length = delay_filter_length

    def get_egress_latency(self) -> int:
        """
        Getter for egress_latency

        Returns:
            int: the egress_latency value
        """
        return self.egress_latency

    def set_egress_latency(self, egress_latency: int) -> None:
        """
        Setter for egress_latency

        Args:
            egress_latency (int): the egress_latency value
        """
        self.egress_latency = egress_latency

    def get_ingress_latency(self) -> int:
        """
        Getter for ingress_latency

        Returns:
            int: the ingress_latency value
        """
        return self.ingress_latency

    def set_ingress_latency(self, ingress_latency: int) -> None:
        """
        Setter for ingress_latency

        Args:
            ingress_latency (int): the ingress_latency value
        """
        self.ingress_latency = ingress_latency

    def get_boundary_clock_jbod(self) -> int:
        """
        Getter for boundary_clock_jbod

        Returns:
            int: the boundary_clock_jbod value
        """
        return self.boundary_clock_jbod

    def set_boundary_clock_jbod(self, boundary_clock_jbod: int) -> None:
        """
        Setter for boundary_clock_jbod

        Args:
            boundary_clock_jbod (int): the boundary_clock_jbod value
        """
        self.boundary_clock_jbod = boundary_clock_jbod
