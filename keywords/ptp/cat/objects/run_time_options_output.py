from keywords.ptp.cat.cat_ptp_table_parser import CatPtpTableParser
from keywords.ptp.cat.objects.run_time_options_object import RunTimeOptionsObject


class RunTimeOptionsOutput:
    """
    This class parses the output of Run time Options

    Example:
        assume_two_step         0
        logging_level           6
        path_trace_enabled      0
        follow_up_info          0
        hybrid_e2e              0
        inhibit_multicast_service       0
        net_sync_monitor        0
        tc_spanning_tree        0
        tx_timestamp_timeout    1
        unicast_listen          0
        unicast_master_table    0
        unicast_req_duration    3600
        use_syslog              1
        verbose                 0
        summary_interval        0
        kernel_leap             1
        check_fup_sync          0

    """

    def __init__(self, run_time_options_output: list[str]):
        """
        Create an internal RunTimeOptionsObject from the passed parameter.

        Args:
            run_time_options_output (list[str]): a list of strings representing the run time options output
        """
        cat_ptp_table_parser = CatPtpTableParser(run_time_options_output)
        output_values = cat_ptp_table_parser.get_output_values_dict()
        self.run_time_options_object = RunTimeOptionsObject()

        if "assume_two_step" in output_values:
            self.run_time_options_object.set_assume_two_step(int(output_values["assume_two_step"]))

        if "logging_level" in output_values:
            self.run_time_options_object.set_logging_level(int(output_values["logging_level"]))

        if "path_trace_enabled" in output_values:
            self.run_time_options_object.set_path_trace_enabled(int(output_values["path_trace_enabled"]))

        if "follow_up_info" in output_values:
            self.run_time_options_object.set_follow_up_info(int(output_values["follow_up_info"]))

        if "hybrid_e2e" in output_values:
            self.run_time_options_object.set_hybrid_e2e(int(output_values["hybrid_e2e"]))

        if "inhibit_multicast_service" in output_values:
            self.run_time_options_object.set_inhibit_multicast_service(int(output_values["inhibit_multicast_service"]))

        if "net_sync_monitor" in output_values:
            self.run_time_options_object.set_net_sync_monitor(int(output_values["net_sync_monitor"]))

        if "tc_spanning_tree" in output_values:
            self.run_time_options_object.set_tc_spanning_tree(int(output_values["tc_spanning_tree"]))

        if "tx_timestamp_timeout" in output_values:
            self.run_time_options_object.set_tx_timestamp_timeout(int(output_values["tx_timestamp_timeout"]))

        if "unicast_listen" in output_values:
            self.run_time_options_object.set_unicast_listen(int(output_values["unicast_listen"]))

        if "unicast_master_table" in output_values:
            self.run_time_options_object.set_unicast_master_table(int(output_values["unicast_master_table"]))

        if "unicast_req_duration" in output_values:
            self.run_time_options_object.set_unicast_req_duration(int(output_values["unicast_req_duration"]))

        if "use_syslog" in output_values:
            self.run_time_options_object.set_use_syslog(int(output_values["use_syslog"]))

        if "verbose" in output_values:
            self.run_time_options_object.set_verbose(int(output_values["verbose"]))

        if "summary_interval" in output_values:
            self.run_time_options_object.set_summary_interval(int(output_values["summary_interval"]))

        if "kernel_leap" in output_values:
            self.run_time_options_object.set_kernel_leap(int(output_values["kernel_leap"]))

        if "check_fup_sync" in output_values:
            self.run_time_options_object.set_check_fup_sync(int(output_values["check_fup_sync"]))

    def get_run_time_options_object(self) -> RunTimeOptionsObject:
        """
        Getter for run_time_options_object object.

        Returns:
            RunTimeOptionsObject: The run time options object containing parsed values.
        """
        return self.run_time_options_object
