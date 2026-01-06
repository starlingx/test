class PMCGetPortDataSetObject:
    """
    Object to hold the values of port data set
    """

    def __init__(self):
        self.port_identity: str = ""
        self.port_state: str = ""
        self.log_min_delay_req_interval: int = -1
        self.peer_mean_path_delay: int = -1
        self.log_announce_interval: int = -1
        self.announce_receipt_timeout: int = -1
        self.log_sync_interval: int = -1
        self.delay_mechanism: int = -1
        self.log_min_p_delay_req_interval: int = -1
        self.version_number: int = -1

    def get_port_identity(self) -> str:
        """
        Getter for port_identity

        Returns: port_identity
        """
        return self.port_identity

    def set_port_identity(self, port_identity: str) -> None:
        """
        Setter for port_identity

        Args:
            port_identity (str): the port_identity value
        Returns: None
        """
        self.port_identity = port_identity

    def get_port_state(self) -> str:
        """
        Getter for port_state

        Returns: port_state
        """
        return self.port_state

    def set_port_state(self, port_state: str) -> None:
        """
        Setter for port_state

        Args:
            port_state (str): the port_state value
        Returns: None
        """
        self.port_state = port_state

    def get_log_min_delay_req_interval(self) -> int:
        """
        Getter for log_min_delay_req_interval

        Returns: log_min_delay_req_interval value
        """
        return self.log_min_delay_req_interval

    def set_log_min_delay_req_interval(self, log_min_delay_req_interval: int) -> None:
        """
        Setter for log_min_delay_req_interval

        Args:
            log_min_delay_req_interval (int): log_min_delay_req_interval value

        Returns: None
        """
        self.log_min_delay_req_interval = log_min_delay_req_interval

    def get_peer_mean_path_delay(self) -> int:
        """
        Getter for peer_mean_path_delay

        Returns: peer_mean_path_delay value
        """
        return self.peer_mean_path_delay

    def set_peer_mean_path_delay(self, peer_mean_path_delay: int) -> None:
        """
        Setter for peer_mean_path_delay

        Args:
            peer_mean_path_delay (int): peer_mean_path_delay value
        Returns: None
        """
        self.peer_mean_path_delay = peer_mean_path_delay

    def get_log_announce_interval(self) -> int:
        """
        Getter for log_announce_interval

        Returns: the log_announce_interval value
        """
        return self.log_announce_interval

    def set_log_announce_interval(self, log_announce_interval: int) -> None:
        """
        Setter for log_announce_interval

        Args:
            log_announce_interval (int): the log_announce_interval value
        Returns: None
        """
        self.log_announce_interval = log_announce_interval

    def get_announce_receipt_timeout(self) -> int:
        """
        Getter for announce_receipt_timeout

        Returns: announce_receipt_timeout value
        """
        return self.announce_receipt_timeout

    def set_announce_receipt_timeout(self, announce_receipt_timeout: int) -> None:
        """
        Setter for announce_receipt_timeout

        Args:
            announce_receipt_timeout (int): the announce_receipt_timeout value
        Returns: None
        """
        self.announce_receipt_timeout = announce_receipt_timeout

    def get_log_sync_interval(self) -> int:
        """
        Getter for log_sync_interval

        Returns: the log_sync_interval value
        """
        return self.log_sync_interval

    def set_log_sync_interval(self, log_sync_interval: int) -> None:
        """
        Setter for log_sync_interval

        Args:
            log_sync_interval (int): the log_sync_interval value
        Returns: None
        """
        self.log_sync_interval = log_sync_interval

    def get_delay_mechanism(self) -> int:
        """
        Getter for delay_mechanism

        Returns: the delay_mechanism value
        """
        return self.delay_mechanism

    def set_delay_mechanism(self, delay_mechanism: int) -> None:
        """
        Setter for delay_mechanism

        Args:
            delay_mechanism (int): the delay_mechanism value
        Returns: None
        """
        self.delay_mechanism = delay_mechanism

    def get_log_min_p_delay_req_interval(self) -> int:
        """
        Getter for log_min_p_delay_req_interval

        Returns: the log_min_p_delay_req_interval value
        """
        return self.log_min_p_delay_req_interval

    def set_log_min_p_delay_req_interval(self, log_min_p_delay_req_interval: int) -> None:
        """
        Setter for log_min_p_delay_req_interval

        Args:
            log_min_p_delay_req_interval (int): the log_min_p_delay_req_interval value
        Returns: None
        """
        self.log_min_p_delay_req_interval = log_min_p_delay_req_interval

    def get_version_number(self) -> int:
        """
        Getter for version_number

        Returns: the version_number value
        """
        return self.version_number

    def set_version_number(self, version_number: int) -> None:
        """
        Setter for version_number

        Args:
            version_number (int): the version_number value
        Returns: None
        """
        self.version_number = version_number
