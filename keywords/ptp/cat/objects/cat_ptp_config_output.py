from keywords.ptp.cat.objects.clock_description_output import ClockDescriptionOutput
from keywords.ptp.cat.objects.default_data_set_output import DefaultDataSetOutput
from keywords.ptp.cat.objects.default_interface_options_output import DefaultInterfaceOptionsOutput
from keywords.ptp.cat.objects.port_data_set_output import PortDataSetOutput
from keywords.ptp.cat.objects.run_time_options_output import RunTimeOptionsOutput
from keywords.ptp.cat.objects.servo_options_output import ServoOptionsOutput
from keywords.ptp.cat.objects.transport_options_output import TransportOptionsOutput


class CATPtpConfigOutput:
    """
    This class parses the output of command cat ' /etc/linuxptp/ptp4l.conf'

    Example:
        [global]
        #
        # Default Data Set
        #
        twoStepFlag             1
        slaveOnly               0
        socket_priority         0
        priority1               128
        priority2               128
        domainNumber            0
        #utc_offset             37
        clockClass              248
        clockAccuracy           0xFE
        offsetScaledLogVariance 0xFFFF
        free_running            0
        freq_est_interval       1
        dscp_event              0
        dscp_general            0
        dataset_comparison      ieee1588
        G.8275.defaultDS.localPriority  128
        maxStepsRemoved         255
        #
        # Port Data Set
        #
        logAnnounceInterval     1
        logSyncInterval         0
        operLogSyncInterval     0
        logMinDelayReqInterval  0
        logMinPdelayReqInterval 0
        operLogPdelayReqInterval 0
        announceReceiptTimeout  3
        syncReceiptTimeout      0
        delayAsymmetry          0
        fault_reset_interval    4
        neighborPropDelayThresh 20000000
        masterOnly              0
        G.8275.portDS.localPriority     128
        asCapable               auto
        BMCA                    ptp
        inhibit_announce        0
        inhibit_delay_req       0
        ignore_source_id        0
        #
        # Run time options
        #
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
        #
        # Servo Options
        #
        pi_proportional_const   0.0
        pi_integral_const       0.0
        pi_proportional_scale   0.0
        pi_proportional_exponent        -0.3
        pi_proportional_norm_max        0.7
        pi_integral_scale       0.0
        pi_integral_exponent    0.4
        pi_integral_norm_max    0.3
        step_threshold          0.0
        first_step_threshold    0.00002
        max_frequency           900000000
        clock_servo             pi
        sanity_freq_limit       200000000
        ntpshm_segment          0
        msg_interval_request    0
        servo_num_offset_values 10
        servo_offset_threshold  0
        write_phase_mode        0
        #
        # Transport options
        #
        transportSpecific       0x0
        ptp_dst_mac             01:1B:19:00:00:00
        p2p_dst_mac             01:80:C2:00:00:0E
        udp_ttl                 1
        udp6_scope              0x0E
        uds_address             /var/run/ptp4l
        uds_ro_address          /var/run/ptp4lro
        #
        # Default interface options
        #
        clock_type              OC
        network_transport       UDPv4
        delay_mechanism         E2E
        time_stamping           hardware
        tsproc_mode             filter
        delay_filter            moving_median
        delay_filter_length     10
        egressLatency           0
        ingressLatency          0
        boundary_clock_jbod     0
        #
        # Clock description
        #
        productDescription      ;;
        revisionData            ;;
        manufacturerIdentity    00:00:00
        userDescription         ;
        timeSource              0xA0

    """

    def __init__(self, cat_config_output: [str]):
        """
        Constructor.
            Create an list of config objects for the given output
        Args:
            cat_config_output (list[str]): a list of strings representing the output of the cat config  command

        """
        self.data_set_output: DefaultDataSetOutput = None
        self.port_data_set_output: PortDataSetOutput = None
        self.run_time_options_output: RunTimeOptionsOutput = None
        self.servo_options_output: ServoOptionsOutput = None
        self.transport_options_output: TransportOptionsOutput = None
        self.default_interface_options_output: DefaultInterfaceOptionsOutput = None
        self.clock_description_output: ClockDescriptionOutput = None

        in_header = False
        in_body = False
        config_object = ''
        body_str = []
        for line in cat_config_output:
            if not in_header and line == '#\n':
                self.create_config_object(config_object, body_str)
                in_header = True
            elif in_header and line != '#\n':
                config_object = line.strip()
            elif line == '#\n' and in_header:  # we are exiting the header
                in_header = False
                in_body = True
                # reset the body str
                body_str = []
            elif in_body:
                body_str.append(line)
        # Create the last config item
        self.create_config_object(config_object, body_str)

    def create_config_object(self, config_object: str, body_str: [str]):
        """
        Creates the config object
        Args:
            config_object (): the object to be created
            body_str (): the body of the config

        Returns:

        """
        if 'Default Data Set' in config_object:
            self.data_set_output = DefaultDataSetOutput(body_str)
        if 'Port Data Set' in config_object:
            self.port_data_set_output = PortDataSetOutput(body_str)
        if 'Run time options' in config_object:
            self.run_time_options_output = RunTimeOptionsOutput(body_str)
        if 'Servo Options' in config_object:
            self.servo_options_output = ServoOptionsOutput(body_str)
        if 'Transport options' in config_object:
            self.transport_options_output = TransportOptionsOutput(body_str)
        if 'Default interface options' in config_object:
            self.default_interface_options_output = DefaultInterfaceOptionsOutput(body_str)
        if 'Clock description' in config_object:
            self.clock_description_output = ClockDescriptionOutput(body_str)

    def get_data_set_output(self) -> DefaultDataSetOutput:
        """
        Getter for the default data set output
        Returns: a PMCGetDefaultDataSetOutput object

        """
        return self.data_set_output

    def get_default_interface_options_output(self) -> DefaultInterfaceOptionsOutput:
        """
        Getter for default interface options ouput
        Returns: a DefaultInterfaceOptionsOutput object

        """
        return self.default_interface_options_output

    def get_port_data_set_output(self) -> PortDataSetOutput:
        """
        Getter for port data set output
        Returns: a PortDataSetOutput object

        """
        return self.port_data_set_output

    def get_run_time_options_output(self) -> RunTimeOptionsOutput:
        """
        Getter for run time options output
        Returns: a RunTimeOptionsOutput object

        """
        return self.run_time_options_output

    def get_servo_options_output(self) -> ServoOptionsOutput:
        """
        Getter for servo options output
        Returns: a ServoOptionsOutput object

        """
        return self.servo_options_output

    def get_transport_options_output(self) -> TransportOptionsOutput:
        """
        Getter for transport options output
        Returns: a TransportOptionsOutput object

        """
        return self.transport_options_output

    def get_clock_description_output(self) -> ClockDescriptionOutput:
        """
        Getter for clock description output
        Returns: a ClockDescriptionOutput object

        """
        return self.clock_description_output
