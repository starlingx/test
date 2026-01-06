class PortDataSetObject:
    """Object to hold the values of port data set"""

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
        self.as_capable: str = ""
        self.bmca: str = ""
        self.inhibit_announce: int = -1
        self.inhibit_delay_req: int = ""
        self.ignore_source_id: int = -1

    def get_log_announce_interval(self) -> int:
        """
        Getter for log_announce_interval

        Returns:
            int: the log_announce_interval value
        """
        return self.log_announce_interval

    def set_log_announce_interval(self, log_announce_interval: int) -> None:
        """
        Setter for two_step_flag

        Args:
            log_announce_interval (int): the log_announce_interval value
        """
        self.log_announce_interval = log_announce_interval

    def get_log_sync_interval(self) -> int:
        """
        Getter for log_sync_interval

        Returns:
            int: the log_sync_interval value
        """
        return self.log_sync_interval

    def set_log_sync_interval(self, log_sync_interval: int) -> None:
        """
        Setter for log_sync_interval

        Args:
            log_sync_interval (int): log_sync_interval value
        """
        self.log_sync_interval = log_sync_interval

    def get_oper_log_sync_interval(self) -> int:
        """
        Getter for oper_log_sync_interval

        Returns:
            int: the oper_log_sync_interval value
        """
        return self.oper_log_sync_interval

    def set_oper_log_sync_interval(self, oper_log_sync_interval: int) -> None:
        """
        Setter for oper_log_sync_interval

        Args:
            oper_log_sync_interval (int): oper_log_sync_interval value
        """
        self.oper_log_sync_interval = oper_log_sync_interval

    def get_log_min_delay_req_interval(self) -> int:
        """
        Getter for log_min_delay_req_interval

        Returns:
            int: the log_min_delay_req_interval value
        """
        return self.log_min_delay_req_interval

    def set_log_min_delay_req_interval(self, log_min_delay_req_interval: int) -> None:
        """
        Setter for log_min_delay_req_interval

        Args:
            log_min_delay_req_interval (int): the log_min_delay_req_interval value
        """
        self.log_min_delay_req_interval = log_min_delay_req_interval

    def get_log_min_p_delay_req_interval(self) -> int:
        """
        Getter for log_min_p_delay_req_interval

        Returns:
            int: the log_min_p_delay_req_interval value
        """
        return self.log_min_p_delay_req_interval

    def set_log_min_p_delay_req_interval(self, log_min_p_delay_req_interval: int) -> None:
        """
        Setter for log_min_p_delay_req_interval

        Args:
            log_min_p_delay_req_interval (int): the log_min_p_delay_req_interval value
        """
        self.log_min_p_delay_req_interval = log_min_p_delay_req_interval

    def get_oper_log_p_delay_req_interval(self) -> int:
        """
        Getter for oper_log_p_delay_req_interval

        Returns:
            int: the oper_log_p_delay_req_interval value
        """
        return self.oper_log_p_delay_req_interval

    def set_oper_log_p_delay_req_interval(self, oper_log_p_delay_req_interval: int) -> None:
        """
        Setter for oper_log_p_delay_req_interval

        Args:
            oper_log_p_delay_req_interval (int): the oper_log_p_delay_req_interval value
        """
        self.oper_log_p_delay_req_interval = oper_log_p_delay_req_interval

    def get_announce_receipt_timeout(self) -> int:
        """
        Getter for announce_receipt_timeout

        Returns:
            int: the announce_receipt_timeout value
        """
        return self.announce_receipt_timeout

    def set_announce_receipt_timeout(self, announce_receipt_timeout: int) -> None:
        """
        Setter for announce_receipt_timeout

        Args:
            announce_receipt_timeout (int): the announce_receipt_timeout value
        """
        self.announce_receipt_timeout = announce_receipt_timeout

    def get_sync_receipt_timeout(self) -> int:
        """
        Getter for sync_receipt_timeout

        Returns:
            int: the sync_receipt_timeout value
        """
        return self.sync_receipt_timeout

    def set_sync_receipt_timeout(self, sync_receipt_timeout: int) -> None:
        """
        Setter for sync_receipt_timeout

        Args:
            sync_receipt_timeout (int): the sync_receipt_timeout value
        """
        self.sync_receipt_timeout = sync_receipt_timeout

    def get_delay_asymmetry(self) -> int:
        """
        Getter for delay_asymmetry

        Returns:
            int: the delay_asymmetry value
        """
        return self.delay_asymmetry

    def set_delay_asymmetry(self, delay_asymmetry: int) -> None:
        """
        Setter for delay_asymmetry

        Args:
            delay_asymmetry (int): the delay_asymmetry value
        """
        self.delay_asymmetry = delay_asymmetry

    def get_fault_reset_interval(self) -> int:
        """
        Getter for fault_reset_interval

        Returns:
            int: the fault_reset_interval value
        """
        return self.fault_reset_interval

    def set_fault_reset_interval(self, fault_reset_interval: int) -> None:
        """
        Setter for fault_reset_interval

        Args:
            fault_reset_interval (int): the fault_reset_interval value
        """
        self.fault_reset_interval = fault_reset_interval

    def get_neighbor_prop_delay_thresh(self) -> int:
        """
        Getter for neighbor_prop_delay_thresh

        Returns:
            int: the neighbor_prop_delay_thresh value
        """
        return self.neighbor_prop_delay_thresh

    def set_neighbor_prop_delay_thresh(self, neighbor_prop_delay_thresh: int) -> None:
        """
        Setter for neighbor_prop_delay_thresh

        Args:
            neighbor_prop_delay_thresh (int): the neighbor_prop_delay_thresh value
        """
        self.neighbor_prop_delay_thresh = neighbor_prop_delay_thresh

    def get_master_only(self) -> int:
        """
        Getter for master_only

        Returns:
            int: the master_only value
        """
        return self.master_only

    def set_master_only(self, master_only: int) -> None:
        """
        Setter for master_only

        Args:
            master_only (int): the master_only value
        """
        self.master_only = master_only

    def get_as_capable(self) -> str:
        """
        Getter for as_capable

        Returns:
            str: the as_capable value
        """
        return self.as_capable

    def set_as_capable(self, as_capable: str) -> None:
        """
        Setter for as_capable

        Args:
            as_capable (str): the as_capable value
        """
        self.as_capable = as_capable

    def get_bmca(self) -> str:
        """
        Getter for bmca

        Returns:
            str: the bmca value
        """
        return self.bmca

    def set_bmca(self, bmca: str) -> None:
        """
        Setter for bmca

        Args:
            bmca (str): the bmca value
        """
        self.bmca = bmca

    def get_inhibit_announce(self) -> int:
        """
        Getter for inhibit_announce

        Returns:
            int: the inhibit_announce value
        """
        return self.inhibit_announce

    def set_inhibit_announce(self, inhibit_announce: int) -> None:
        """
        Setter for inhibit_announce

        Args:
            inhibit_announce (int): the inhibit_announce value
        """
        self.inhibit_announce = inhibit_announce

    def get_inhibit_delay_req(self) -> int:
        """
        Getter for inhibit_delay_req

        Returns:
            int: the inhibit_delay_req value
        """
        return self.inhibit_delay_req

    def set_inhibit_delay_req(self, inhibit_delay_req: int) -> None:
        """
        Setter for inhibit_delay_req

        Args:
            inhibit_delay_req (int): the inhibit_delay_req value
        """
        self.inhibit_delay_req = inhibit_delay_req

    def get_ignore_source_id(self) -> int:
        """
        Getter for ignore_source_id

        Returns:
            int: the ignore_source_id value
        """
        return self.ignore_source_id

    def set_ignore_source_id(self, ignore_source_id: int) -> None:
        """
        Setter for ignore_source_id

        Args:
            ignore_source_id (int): the ignore_source_id value
        """
        self.ignore_source_id = ignore_source_id
