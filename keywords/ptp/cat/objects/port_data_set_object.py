class PortDataSetObject:
    """
    Object to hold the values of port data set
    """

    def __init__(self):
        self.log_announce_interval: int = -1
        self.log_sync_interval: int = -1
        self.oper_log_sync_interval: int = -1
        self.log_min_delay_req_interval: int = -1
        self.log_min_p_delay_req_interval: int = -1
        self.oper_log_p_delay_req_interval: int = -1
        self.announce_receipt_timeout: int = -1
        self.sync_receipt_timeout: int = -1
        self.delay_asymmetry: int = -1
        self.fault_reset_interval: int = -1
        self.neighbor_prop_delay_thresh: int = -1
        self.master_only: int = -1
        self.as_capable: str = ''
        self.bmca: str = ''
        self.inhibit_announce: int = -1
        self.inhibit_delay_req: int = ''
        self.ignore_source_id: int = -1

    def get_log_announce_interval(self) -> int:
        """
        Getter for log_announce_interval
        Returns: log_announce_interval

        """
        return self.log_announce_interval

    def set_log_announce_interval(self, log_announce_interval: int):
        """
        Setter for two_step_flag
        Args:
            log_announce_interval (): the log_announce_interval value

        Returns:

        """
        self.log_announce_interval = log_announce_interval

    def get_log_sync_interval(self) -> int:
        """
        Getter for log_sync_interval
        Returns: log_sync_interval value

        """
        return self.log_sync_interval

    def set_log_sync_interval(self, log_sync_interval: int):
        """
        Setter for log_sync_interval
        Args:
            log_sync_interval (): log_sync_interval value

        Returns:

        """
        self.log_sync_interval = log_sync_interval

    def get_oper_log_sync_interval(self) -> int:
        """
        Getter for oper_log_sync_interval
        Returns: oper_log_sync_interval value

        """
        return self.oper_log_sync_interval

    def set_oper_log_sync_interval(self, oper_log_sync_interval: int):
        """
        Setter for oper_log_sync_interval
        Args:
            oper_log_sync_interval (): oper_log_sync_interval value

        Returns:

        """
        self.oper_log_sync_interval = oper_log_sync_interval

    def get_log_min_delay_req_interval(self) -> int:
        """
        Getter for log_min_delay_req_interval
        Returns: the log_min_delay_req_interval value

        """
        return self.log_min_delay_req_interval

    def set_log_min_delay_req_interval(self, log_min_delay_req_interval: int):
        """
        Setter for log_min_delay_req_interval
        Args:
            log_min_delay_req_interval (): the log_min_delay_req_interval value

        Returns:

        """
        self.log_min_delay_req_interval = log_min_delay_req_interval

    def get_log_min_p_delay_req_interval(self) -> int:
        """
        Getter for log_min_p_delay_req_interval
        Returns: log_min_p_delay_req_interval value

        """
        return self.log_min_p_delay_req_interval

    def set_log_min_p_delay_req_interval(self, log_min_p_delay_req_interval: int):
        """
        Setter for log_min_p_delay_req_interval
        Args:
            log_min_p_delay_req_interval (): the log_min_p_delay_req_interval value

        Returns:

        """
        self.log_min_p_delay_req_interval = log_min_p_delay_req_interval

    def get_oper_log_p_delay_req_interval(self) -> int:
        """
        Getter for oper_log_p_delay_req_interval
        Returns: the oper_log_p_delay_req_interval value

        """
        return self.oper_log_p_delay_req_interval

    def set_oper_log_p_delay_req_interval(self, oper_log_p_delay_req_interval: int):
        """
        Setter for oper_log_p_delay_req_interval
        Args:
            oper_log_p_delay_req_interval (): the oper_log_p_delay_req_interval value

        Returns:

        """
        self.oper_log_p_delay_req_interval = oper_log_p_delay_req_interval

    def get_announce_receipt_timeout(self) -> int:
        """
        Getter for announce_receipt_timeout
        Returns: the announce_receipt_timeout value

        """
        return self.announce_receipt_timeout

    def set_announce_receipt_timeout(self, announce_receipt_timeout: int):
        """
        Setter for announce_receipt_timeout
        Args:
            announce_receipt_timeout (): the announce_receipt_timeout value

        Returns:

        """
        self.announce_receipt_timeout = announce_receipt_timeout

    def get_sync_receipt_timeout(self) -> int:
        """
        Getter for sync_receipt_timeout
        Returns: the sync_receipt_timeout value

        """
        return self.sync_receipt_timeout

    def set_sync_receipt_timeout(self, sync_receipt_timeout: int):
        """
        Setter for sync_receipt_timeout
        Args:
            sync_receipt_timeout (): the sync_receipt_timeout value

        Returns:

        """
        self.sync_receipt_timeout = sync_receipt_timeout

    def get_delay_asymmetry(self) -> int:
        """
        Getter for delay_asymmetry
        Returns: the delay_asymmetry value

        """
        return self.delay_asymmetry

    def set_delay_asymmetry(self, delay_asymmetry: int):
        """
        Setter for delay_asymmetry
        Args:
            delay_asymmetry (): the delay_asymmetry value

        Returns:

        """
        self.delay_asymmetry = delay_asymmetry

    def get_fault_reset_interval(self) -> int:
        """
        Getter for fault_reset_interval
        Returns: the fault_reset_interval value

        """
        return self.fault_reset_interval

    def set_fault_reset_interval(self, fault_reset_interval: int):
        """
        Setter for fault_reset_interval
        Args:
            fault_reset_interval (): the fault_reset_interval value

        Returns:

        """
        self.fault_reset_interval = fault_reset_interval

    def get_neighbor_prop_delay_thresh(self) -> int:
        """
        Getter for neighbor_prop_delay_thresh
        Returns: the neighbor_prop_delay_thresh value

        """
        return self.neighbor_prop_delay_thresh

    def set_neighbor_prop_delay_thresh(self, neighbor_prop_delay_thresh: int):
        """
        Setter for neighbor_prop_delay_thresh
        Args:
            neighbor_prop_delay_thresh (): the neighbor_prop_delay_thresh value

        Returns:

        """
        self.neighbor_prop_delay_thresh = neighbor_prop_delay_thresh

    def get_master_only(self) -> int:
        """
        Getter for master_only
        Returns: the master_only value

        """
        return self.master_only

    def set_master_only(self, master_only: int):
        """
        Setter for master_only
        Args:
            master_only (): the master_only value

        Returns:

        """
        self.master_only = master_only

    def get_as_capable(self) -> str:
        """
        Getter for as_capable
        Returns: the as_capable value

        """
        return self.as_capable

    def set_as_capable(self, as_capable: str):
        """
        Setter for as_capable
        Args:
            as_capable (): the as_capable value

        Returns:

        """
        self.as_capable = as_capable

    def get_bmca(self) -> str:
        """
        Getter for bmca
        Returns: the bmca value

        """
        return self.bmca

    def set_bmca(self, bmca: str):
        """
        Setter for bmca
        Args:
            bmca (): the bmca value

        Returns:

        """
        self.bmca = bmca

    def get_inhibit_announce(self) -> int:
        """
        Getter for inhibit_announce
        Returns: the inhibit_announce value

        """
        return self.inhibit_announce

    def set_inhibit_announce(self, inhibit_announce: int):
        """
        Setter for inhibit_announce
        Args:
            inhibit_announce (): the inhibit_announce value

        Returns:

        """
        self.inhibit_announce = inhibit_announce

    def get_inhibit_delay_req(self) -> int:
        """
        Getter for inhibit_delay_req
        Returns: the inhibit_delay_req value

        """
        return self.inhibit_delay_req

    def set_inhibit_delay_req(self, inhibit_delay_req: int):
        """
        Setter for inhibit_delay_req
        Args:
            inhibit_delay_req (): the inhibit_delay_req value

        Returns:

        """
        self.inhibit_delay_req = inhibit_delay_req

    def get_ignore_source_id(self) -> int:
        """
        Getter for ignore_source_id
        Returns: the ignore_source_id value

        """
        return self.ignore_source_id

    def set_ignore_source_id(self, ignore_source_id: int):
        """
        Setter for ignore_source_id
        Args:
            ignore_source_id (): the ignore_source_id value

        Returns:

        """
        self.ignore_source_id = ignore_source_id





