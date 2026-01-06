from keywords.ptp.cat.objects.cat_ptp_config_output import CATPtpConfigOutput

cat_ptp_config = [
    "[global] \n",
    "#\n",
    "# Default Data Set\n",
    "#\n",
    "twoStepFlag             1\n",
    "slaveOnly               0\n",
    "socket_priority         0\n",
    "priority1               128\n",
    "priority2               128\n",
    "domainNumber            0\n",
    "#utc_offset             37\n",
    "clockClass              248\n",
    "clockAccuracy           0xFE\n",
    "offsetScaledLogVariance 0xFFFF\n",
    "free_running            0\n",
    "freq_est_interval       1\n",
    "dscp_event              0\n",
    "dscp_general            0\n",
    "dataset_comparison      ieee1588\n",
    "G.8275.defaultDS.localPriority  128\n",
    "maxStepsRemoved         255\n",
    "#\n",
    "# Port Data Set\n",
    "#\n",
    "logAnnounceInterval     1\n",
    "logSyncInterval         0\n",
    "operLogSyncInterval     0\n",
    "logMinDelayReqInterval  0\n",
    "logMinPdelayReqInterval 0\n",
    "operLogPdelayReqInterval 0\n",
    "announceReceiptTimeout  3\n",
    "syncReceiptTimeout      0\n",
    "delayAsymmetry          0\n",
    "fault_reset_interval    4\n",
    "neighborPropDelayThresh 20000000\n",
    "masterOnly              0\n",
    "G.8275.portDS.localPriority     128\n",
    "asCapable               auto\n",
    "BMCA                    ptp\n",
    "inhibit_announce        0\n",
    "inhibit_delay_req       0\n",
    "ignore_source_id        0\n",
    "#\n",
    "# Run time options\n",
    "#\n",
    "assume_two_step         0\n",
    "logging_level           6\n",
    "path_trace_enabled      0\n",
    "follow_up_info          0\n",
    "hybrid_e2e              0\n",
    "inhibit_multicast_service       0\n",
    "net_sync_monitor        0\n",
    "tc_spanning_tree        0\n",
    "tx_timestamp_timeout    1\n",
    "unicast_listen          0\n",
    "unicast_master_table    0\n",
    "unicast_req_duration    3600\n",
    "use_syslog              1\n",
    "verbose                 0\n",
    "summary_interval        0\n",
    "kernel_leap             1\n",
    "check_fup_sync          0\n",
    "#\n",
    "# Servo Options\n",
    "#\n",
    "pi_proportional_const   0.0\n",
    "pi_integral_const       0.0\n",
    "pi_proportional_scale   0.0\n",
    "pi_proportional_exponent        -0.3\n",
    "pi_proportional_norm_max        0.7\n",
    "pi_integral_scale       0.0\n",
    "pi_integral_exponent    0.4\n",
    "pi_integral_norm_max    0.3\n",
    "step_threshold          0.0\n",
    "first_step_threshold    0.00002\n",
    "max_frequency           900000000\n",
    "clock_servo             pi\n",
    "sanity_freq_limit       200000000\n",
    "ntpshm_segment          0\n",
    "msg_interval_request    0\n",
    "servo_num_offset_values 10\n",
    "servo_offset_threshold  0\n",
    "write_phase_mode        0\n",
    "#\n",
    "# Transport options\n",
    "#\n",
    "transportSpecific       0x0\n",
    "ptp_dst_mac             01:1B:19:00:00:00\n",
    "p2p_dst_mac             01:80:C2:00:00:0E\n",
    "udp_ttl                 1\n",
    "udp6_scope              0x0E\n",
    "uds_address             /var/run/ptp4l\n",
    "uds_ro_address          /var/run/ptp4lro\n",
    "#\n",
    "# Default interface options\n",
    "#\n",
    "clock_type              OC\n",
    "network_transport       UDPv4\n",
    "delay_mechanism         E2E\n",
    "time_stamping           hardware\n",
    "tsproc_mode             filter\n",
    "delay_filter            moving_median\n",
    "delay_filter_length     10\n",
    "egressLatency           0\n",
    "ingressLatency          0\n",
    "boundary_clock_jbod     0\n",
    "#\n",
    "# Clock description\n",
    "#\n",
    "productDescription      ;;\n",
    "revisionData            ;;\n",
    "manufacturerIdentity    00:00:00\n",
    "userDescription         ;\n",
    "timeSource              0xA0\n",
]

# fmt: off
cat_ptp_config_with_associated_interfaces = [
    "[global]\n",
    "##\n",
    "## Default Data Set\n",
    "##\n", "boundary_clock_jbod 1\n",
    "clock_servo linreg\n",
    "dataset_comparison G.8275.x\n",
    "delay_mechanism E2E\n",
    "domainNumber 24\n",
    "message_tag ptp1\n",
    "network_transport L2\n",
    "priority2 100\n",
    "summary_interval 6\n",
    "time_stamping hardware\n",
    "tx_timestamp_timeout 700\n",
    "uds_address /var/run/ptp4l-ptp1\n",
    "\n",
    "\n",
    "\n",
    "[enp81s0f1]\n",
    "##\n",
    "## Associated interface: enp81s0f1\n",
    "##\n",
    "\n",
    "[enp81s0f2]\n",
    "##\n",
    "## Associated interface: enp81s0f2\n",
    "##\n",
    "\n"
]


def test_cat_ptp_config_output():
    """
    Tests cat_ptp_config_output

    """
    cat_ptp_config_output = CATPtpConfigOutput(cat_ptp_config)

    # validate default data set
    default_data_set_object = cat_ptp_config_output.get_data_set_output().get_pmc_get_default_data_set_object()
    assert default_data_set_object.get_two_step_flag() == 1
    assert default_data_set_object.get_slave_only() == 0
    assert default_data_set_object.get_socket_priority() == 0
    assert default_data_set_object.get_priority1() == 128
    assert default_data_set_object.get_priority2() == 128
    assert default_data_set_object.get_domain_number() == 0
    assert default_data_set_object.get_utc_offset() == 37
    assert default_data_set_object.get_clock_class() == 248
    assert default_data_set_object.get_clock_accuracy() == "0xFE"
    assert default_data_set_object.get_offset_scaled_log_variance() == "0xFFFF"
    assert default_data_set_object.get_free_running() == 0
    assert default_data_set_object.get_freq_est_interval() == 1
    assert default_data_set_object.get_dscp_event() == 0
    assert default_data_set_object.get_dscp_general() == 0
    assert default_data_set_object.get_dataset_comparison() == "ieee1588"
    assert default_data_set_object.get_max_steps_removed() == 255

    # validate the port data object
    port_data_object = cat_ptp_config_output.get_port_data_set_output().get_port_data_set_object()
    assert port_data_object.get_log_announce_interval() == 1
    assert port_data_object.get_log_sync_interval() == 0
    assert port_data_object.get_oper_log_sync_interval() == 0
    assert port_data_object.get_log_min_delay_req_interval() == 0
    assert port_data_object.get_log_min_p_delay_req_interval() == 0
    assert port_data_object.get_oper_log_p_delay_req_interval() == 0
    assert port_data_object.get_announce_receipt_timeout() == 3
    assert port_data_object.get_sync_receipt_timeout() == 0
    assert port_data_object.get_delay_asymmetry() == 0
    assert port_data_object.get_fault_reset_interval() == 4
    assert port_data_object.get_neighbor_prop_delay_thresh() == 20000000
    assert port_data_object.get_master_only() == 0
    assert port_data_object.get_as_capable() == "auto"
    assert port_data_object.get_bmca() == "ptp"
    assert port_data_object.get_inhibit_announce() == 0
    assert port_data_object.get_inhibit_delay_req() == 0
    assert port_data_object.get_ignore_source_id() == 0

    # validate run time options
    run_time_options_object = cat_ptp_config_output.get_run_time_options_output().get_run_time_options_object()
    assert run_time_options_object.get_assume_two_step() == 0
    assert run_time_options_object.get_logging_level() == 6
    assert run_time_options_object.get_path_trace_enabled() == 0
    assert run_time_options_object.get_follow_up_info() == 0
    assert run_time_options_object.get_hybrid_e2e() == 0
    assert run_time_options_object.get_inhibit_multicast_service() == 0
    assert run_time_options_object.get_net_sync_monitor() == 0
    assert run_time_options_object.get_tc_spanning_tree() == 0
    assert run_time_options_object.get_tx_timestamp_timeout() == 1
    assert run_time_options_object.get_unicast_listen() == 0
    assert run_time_options_object.get_unicast_master_table() == 0
    assert run_time_options_object.get_unicast_req_duration() == 3600
    assert run_time_options_object.get_use_syslog() == 1
    assert run_time_options_object.get_verbose() == 0
    assert run_time_options_object.get_summary_interval() == 0
    assert run_time_options_object.get_kernel_leap() == 1
    assert run_time_options_object.get_check_fup_sync() == 0

    # validate Servo Options
    servo_options_object = cat_ptp_config_output.get_servo_options_output().get_servo_options_object()
    assert servo_options_object.get_pi_proportional_const() == 0.0
    assert servo_options_object.get_pi_integral_const() == 0.0
    assert servo_options_object.get_pi_proportional_scale() == 0.0
    assert servo_options_object.get_pi_proportional_exponent() == -0.3
    assert servo_options_object.get_pi_proportional_norm_max() == 0.7
    assert servo_options_object.get_pi_integral_scale() == 0.0
    assert servo_options_object.get_pi_integral_exponent() == 0.4
    assert servo_options_object.get_pi_integral_norm_max() == 0.3
    assert servo_options_object.get_step_threshold() == 0.0
    assert servo_options_object.get_first_step_threshold() == 0.00002
    assert servo_options_object.get_max_frequency() == 900000000
    assert servo_options_object.get_clock_servo() == "pi"
    assert servo_options_object.get_sanity_freq_limit() == 200000000
    assert servo_options_object.get_ntpshm_segment() == 0
    assert servo_options_object.get_msg_interval_request() == 0
    assert servo_options_object.get_servo_num_offset_values() == 10
    assert servo_options_object.get_servo_offset_threshold() == 0
    assert servo_options_object.get_write_phase_mode() == 0

    # validate transport options

    transport_options_object = cat_ptp_config_output.get_transport_options_output().get_transport_options_object()
    assert transport_options_object.get_transport_specific() == "0x0"
    assert transport_options_object.get_ptp_dst_mac() == "01:1B:19:00:00:00"
    assert transport_options_object.get_p2p_dst_mac() == "01:80:C2:00:00:0E"
    assert transport_options_object.get_udp_ttl() == 1
    assert transport_options_object.get_udp6_scope() == "0x0E"
    assert transport_options_object.get_uds_address() == "/var/run/ptp4l"
    assert transport_options_object.get_uds_ro_address() == "/var/run/ptp4lro"

    # validate default interface options
    default_interface_object = cat_ptp_config_output.get_default_interface_options_output().get_default_interface_options_object()
    assert default_interface_object.get_clock_type() == "OC"
    assert default_interface_object.get_network_transport() == "UDPv4"
    assert default_interface_object.get_delay_mechanism() == "E2E"
    assert default_interface_object.get_time_stamping() == "hardware"
    assert default_interface_object.get_tsproc_mode() == "filter"
    assert default_interface_object.get_delay_filter() == "moving_median"
    assert default_interface_object.get_delay_filter_length() == 10
    assert default_interface_object.get_egress_latency() == 0
    assert default_interface_object.get_ingress_latency() == 0
    assert default_interface_object.get_boundary_clock_jbod() == 0

    # validate clock description
    clock_description_object = cat_ptp_config_output.get_clock_description_output().get_clock_description_object()
    assert clock_description_object.get_product_description() == ";;"
    assert clock_description_object.get_revision_data() == ";;"
    assert clock_description_object.get_manufacturer_identity() == "00:00:00"
    assert clock_description_object.get_user_description() == ";"
    assert clock_description_object.get_time_source() == "0xA0"


def test_cat_ptp_output_format_with_associated_interfaces():
    """
    Test to validate output with associated interfaces

    """
    cat_ptp_config_output = CATPtpConfigOutput(cat_ptp_config_with_associated_interfaces)

    # validate default data set
    default_data_set_object = cat_ptp_config_output.get_data_set_output().get_pmc_get_default_data_set_object()
    assert default_data_set_object.get_boundary_clock_jbod() == 1
    assert default_data_set_object.get_clock_servo() == "linreg"
    assert default_data_set_object.get_dataset_comparison() == "G.8275.x"
    assert default_data_set_object.get_delay_mechanism() == "E2E"
    assert default_data_set_object.get_domain_number() == 24
    assert default_data_set_object.get_message_tag() == "ptp1"
    assert default_data_set_object.get_network_transport() == "L2"
    assert default_data_set_object.get_priority2() == 100
    assert default_data_set_object.get_summary_interval() == 6
    assert default_data_set_object.get_time_stamping() == "hardware"
    assert default_data_set_object.get_uds_address() == "/var/run/ptp4l-ptp1"

    assert cat_ptp_config_output.get_associated_interfaces() == ["enp81s0f1", "enp81s0f2"]
