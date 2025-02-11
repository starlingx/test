class RunTimeOptionsObject:
    """
    Object to hold the values of Run time Options
    """

    def __init__(self):
        self.assume_two_step: int = -1
        self.logging_level: int = -1
        self.path_trace_enabled: int = -1
        self.follow_up_info: int = -1
        self.hybrid_e2e: int = -1
        self.inhibit_multicast_service: int = -1
        self.net_sync_monitor: int = -1
        self.tc_spanning_tree: int = -1
        self.tx_timestamp_timeout: int = -1
        self.unicast_listen: int = -1
        self.unicast_master_table: int = -1
        self.unicast_req_duration: int = -1
        self.use_syslog: int = -1
        self.verbose: int = -1
        self.summary_interval: int = -1
        self.kernel_leap: int = ''
        self.check_fup_sync: int = -1

    def get_assume_two_step(self) -> int:
        """
        Getter for assume_two_step
        Returns: assume_two_step

        """
        return self.assume_two_step

    def set_assume_two_step(self, assume_two_step: int):
        """
        Setter for assume_two_step
        Args:
            assume_two_step (): the assume_two_step value

        Returns:

        """
        self.assume_two_step = assume_two_step

    def get_logging_level(self) -> int:
        """
        Getter for logging_level
        Returns: logging_level value

        """
        return self.logging_level

    def set_logging_level(self, logging_level: int):
        """
        Setter for logging_level
        Args:
            log_sync_interval (): log_sync_interval value

        Returns:

        """
        self.logging_level = logging_level

    def get_path_trace_enabled(self) -> int:
        """
        Getter for path_trace_enabled
        Returns: path_trace_enabled value

        """
        return self.path_trace_enabled

    def set_path_trace_enabled(self, path_trace_enabled: int):
        """
        Setter for path_trace_enabled
        Args:
            path_trace_enabled (): path_trace_enabled value

        Returns:

        """
        self.path_trace_enabled = path_trace_enabled

    def get_follow_up_info(self) -> int:
        """
        Getter for follow_up_info
        Returns: the follow_up_info value

        """
        return self.follow_up_info

    def set_follow_up_info(self, follow_up_info: int):
        """
        Setter for follow_up_info
        Args:
            follow_up_info (): the follow_up_info value

        Returns:

        """
        self.follow_up_info = follow_up_info

    def get_hybrid_e2e(self) -> int:
        """
        Getter for hybrid_e2e
        Returns: hybrid_e2e value

        """
        return self.hybrid_e2e

    def set_hybrid_e2e(self, hybrid_e2e: int):
        """
        Setter for hybrid_e2e
        Args:
            hybrid_e2e (): the hybrid_e2e value

        Returns:

        """
        self.hybrid_e2e = hybrid_e2e

    def get_inhibit_multicast_service(self) -> int:
        """
        Getter for inhibit_multicast_service
        Returns: the inhibit_multicast_service value

        """
        return self.inhibit_multicast_service

    def set_inhibit_multicast_service(self, inhibit_multicast_service: int):
        """
        Setter for inhibit_multicast_service
        Args:
            inhibit_multicast_service (): the inhibit_multicast_service value

        Returns:

        """
        self.inhibit_multicast_service = inhibit_multicast_service

    def get_net_sync_monitor(self) -> int:
        """
        Getter for net_sync_monitor
        Returns: the net_sync_monitor value

        """
        return self.net_sync_monitor

    def set_net_sync_monitor(self, net_sync_monitor: int):
        """
        Setter for net_sync_monitor
        Args:
            net_sync_monitor (): the net_sync_monitor value

        Returns:

        """
        self.net_sync_monitor = net_sync_monitor

    def get_tc_spanning_tree(self) -> int:
        """
        Getter for tc_spanning_tree
        Returns: the tc_spanning_tree value

        """
        return self.tc_spanning_tree

    def set_tc_spanning_tree(self, tc_spanning_tree: int):
        """
        Setter for sync_receipt_timeout
        Args:
            tc_spanning_tree (): the tc_spanning_tree value

        Returns:

        """
        self.tc_spanning_tree = tc_spanning_tree

    def get_tx_timestamp_timeout(self) -> int:
        """
        Getter for tx_timestamp_timeout
        Returns: the tx_timestamp_timeout value

        """
        return self.tx_timestamp_timeout

    def set_tx_timestamp_timeout(self, tx_timestamp_timeout: int):
        """
        Setter for tx_timestamp_timeout
        Args:
            tx_timestamp_timeout (): the tx_timestamp_timeout value

        Returns:

        """
        self.tx_timestamp_timeout = tx_timestamp_timeout

    def get_unicast_listen(self) -> int:
        """
        Getter for unicast_listen
        Returns: the unicast_listen value

        """
        return self.unicast_listen

    def set_unicast_listen(self, unicast_listen: int):
        """
        Setter for unicast_listen
        Args:
            unicast_listen (): the unicast_listen value

        Returns:

        """
        self.unicast_listen = unicast_listen

    def get_unicast_master_table(self) -> int:
        """
        Getter for unicast_master_table
        Returns: the unicast_master_table value

        """
        return self.unicast_master_table

    def set_unicast_master_table(self, unicast_master_table: int):
        """
        Setter for unicast_master_table
        Args:
            unicast_master_table (): the unicast_master_table value

        Returns:

        """
        self.unicast_master_table = unicast_master_table

    def get_unicast_req_duration(self) -> int:
        """
        Getter for unicast_req_duration
        Returns: the unicast_req_duration value

        """
        return self.unicast_req_duration

    def set_unicast_req_duration(self, unicast_req_duration: int):
        """
        Setter for unicast_req_duration
        Args:
            unicast_req_duration (): the unicast_req_duration value

        Returns:

        """
        self.unicast_req_duration = unicast_req_duration

    def get_use_syslog(self) -> int:
        """
        Getter for use_syslog
        Returns: the use_syslog value

        """
        return self.use_syslog

    def set_use_syslog(self, use_syslog: int):
        """
        Setter for use_syslog
        Args:
            use_syslog (): the use_syslog value

        Returns:

        """
        self.use_syslog = use_syslog

    def get_verbose(self) -> int:
        """
        Getter for verbose
        Returns: the verbose value

        """
        return self.verbose

    def set_verbose(self, verbose: int):
        """
        Setter for verbose
        Args:
            verbose (): the verbose value

        Returns:

        """
        self.verbose = verbose

    def get_summary_interval(self) -> int:
        """
        Getter for summary_interval
        Returns: the summary_interval value

        """
        return self.summary_interval

    def set_summary_interval(self, summary_interval: int):
        """
        Setter for summary_interval
        Args:
            summary_interval (): the summary_interval value

        Returns:

        """
        self.summary_interval = summary_interval

    def get_kernel_leap(self) -> int:
        """
        Getter for kernel_leap
        Returns: the kernel_leap value

        """
        return self.kernel_leap

    def set_kernel_leap(self, kernel_leap: int):
        """
        Setter for kernel_leap
        Args:
            kernel_leap (): the kernel_leap value

        Returns:

        """
        self.kernel_leap = kernel_leap

    def get_check_fup_sync(self) -> int:
        """
        Getter for check_fup_sync
        Returns: the check_fup_sync value

        """
        return self.check_fup_sync

    def set_check_fup_sync(self, check_fup_sync: int):
        """
        Setter for check_fup_sync
        Args:
            check_fup_sync (): the check_fup_sync value

        Returns:

        """
        self.check_fup_sync = check_fup_sync






