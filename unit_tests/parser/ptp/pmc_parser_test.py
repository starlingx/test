from keywords.ptp.pmc.objects.pmc_get_current_data_set_output import PMCGetCurrentDataSetOutput
from keywords.ptp.pmc.objects.pmc_get_default_data_set_output import PMCGetDefaultDataSetOutput
from keywords.ptp.pmc.objects.pmc_get_domain_output import PMCGetDomainOutput
from keywords.ptp.pmc.objects.pmc_get_grandmaster_settings_np_output import PMCGetGrandmasterSettingsNpOutput
from keywords.ptp.pmc.objects.pmc_get_parent_data_set_output import PMCGetParentDataSetOutput
from keywords.ptp.pmc.objects.pmc_get_port_data_set_output import PMCGetPortDataSetOutput
from keywords.ptp.pmc.objects.pmc_get_time_properties_data_set_output import PMCGetTimePropertiesDataSetOutput
from keywords.ptp.pmc.objects.pmc_get_time_status_np_output import PMCGetTimeStatusNpOutput
from keywords.ptp.pmc.pmc_table_parser import PMCTableParser

pmc_output = [
    "sending: GET DEFAULT_DATA_SET\n",
    "   507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT DEFAULT_DATA_SET\n",
    "       twoStepFlag            1\n",
    "       slaveOnly              0\n",
    "       numberPorts            1\n",
    "       priority1              128\n",
    "       clockClass             248\n",
    "       clockAccuracy          0xfe\n",
    "       offsetScaledLogVariance 0xffff\n",
    "       priority2              128\n",
    "       clockIdentity          507c6f.fffe.0b5a4d\n",
    "       domainNumber           0\n",
    "sysadmin@controller-0:~$\n",
]

pmc_parent_data_set_output = [
    "sending: GET PARENT_DATA_SET\n",
    "   507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT PARENT_DATA_SET\n",
    "       parentPortIdentity                    507c6f.fffe.0b5a4d-0\n",
    "       parentStats                           0\n",
    "       observedParentOffsetScaledLogVariance 0xffff\n",
    "       observedParentClockPhaseChangeRate    0x7fffffff\n",
    "       grandmasterPriority1                  128\n",
    "       gm.ClockClass                         248\n",
    "       gm.ClockAccuracy                      0xfe\n",
    "       gm.OffsetScaledLogVariance            0xffff\n",
    "       grandmasterPriority2                  128\n",
    "       grandmasterIdentity                   507c6f.fffe.0b5a4d\n",
    "sysadmin@controller-0:~$\n",
]

pmc_get_current_data_set_output = [
    "sending: GET CURRENT_DATA_SET\n",
    "   507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT CURRENT_DATA_SET\n",
    "       stepsRemoved     3\n",
    "       offsetFromMaster 1.3\n",
    "       meanPathDelay    2.5\n",
    "sysadmin@controller-0:~$\n",
]

pmc_get_domain_output = [
    "sending: GET DOMAIN\n",
    "   507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT DOMAIN\n",
    "   domainNumber 24\n",
    "sysadmin@controller-0:~$\n",
]

pmc_get_grandmaster_settings_output = [
    "sending: GET GRANDMASTER_SETTINGS_NP\n",
    "   507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT GRANDMASTER_SETTINGS_NP\n",
    "       clockClass              6\n",
    "       clockAccuracy           0x20\n",
    "       offsetScaledLogVariance 0x4e5d\n",
    "       currentUtcOffset        37\n",
    "       leap61                  0\n",
    "       leap59                  0\n",
    "       currentUtcOffsetValid   0\n",
    "       ptpTimescale            1\n",
    "       timeTraceable           1\n",
    "       frequencyTraceable      1\n",
    "       timeSource              0x20\n",
    "sysadmin@controller-0:~$\n",
]

pmc_get_time_properties_data_set_output = [
    "sending: GET TIME_PROPERTIES_DATA_SET\n",
    "   507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT TIME_PROPERTIES_DATA_SET\n",
    "       currentUtcOffset      37\n",
    "       leap61                0\n",
    "       leap59                0\n",
    "       currentUtcOffsetValid 0\n",
    "       ptpTimescale          1\n",
    "       timeTraceable         1\n",
    "       frequencyTraceable    0\n",
    "       timeSource            0x20\n",
    "sysadmin@controller-0:~$\n",
]

pmc_get_time_status_output = [
    "sending: GET TIME_STATUS_NP\n",
    "   507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT TIME_STATUS_NP\n",
    "       master_offset              -62\n",
    "       ingress_time               0\n",
    "       cumulativeScaledRateOffset +0.000000000\n",
    "       scaledLastGmPhaseChange    0\n",
    "       gmTimeBaseIndicator        0\n",
    "       lastGmPhaseChange          0x00000000000000000000.0000\n",
    "       gmPresent                  false\n",
    "       gmIdentity                 507c6f.fffe.0b5a4d\n",
    "sysadmin@controller-0:~$\n",
]

pmc_get_port_data_set_output = ["sending: GET PORT_DATA_SET\n", "   b48351.fffe.0a37b0-1 seq 0 RESPONSE MANAGEMENT PORT_DATA_SET \n", "       portIdentity            b48351.fffe.0a37b0-1\n", "       portState               SLAVE\n", "       logMinDelayReqInterval  0\n", "       peerMeanPathDelay       0\n", "       logAnnounceInterval     1\n", "       announceReceiptTimeout  3\n", "       logSyncInterval         0\n", "       delayMechanism          1\n", "       logMinPdelayReqInterval 0\n", "       versionNumber           2\n", "   b48351.fffe.0a37b0-2 seq 0 RESPONSE MANAGEMENT PORT_DATA_SET \n", "       portIdentity            b48351.fffe.0a37b0-2\n", "       portState               MASTER\n", "       logMinDelayReqInterval  0\n", "       peerMeanPathDelay       0\n", "       logAnnounceInterval     1\n", "       announceReceiptTimeout  3\n", "       logSyncInterval         0\n", "       delayMechanism          1\n", "       logMinPdelayReqInterval 0\n", "       versionNumber           2\n", "sysadmin@controller-1:~$ \n"]


def test_pmc_get_default_data_set_table_parser():
    """
    Tests the pmc table parser for get_default_data_set output parser

    """
    pmc_table_parser = PMCTableParser(pmc_output)

    output_dict_list = pmc_table_parser.get_output_values_dict()
    assert len(output_dict_list) == 1, "more than 1 default data set was found"

    output_dict = output_dict_list[0]

    assert output_dict["twoStepFlag"] == "1"
    assert output_dict["slaveOnly"] == "0"
    assert output_dict["numberPorts"] == "1"
    assert output_dict["priority1"] == "128"
    assert output_dict["clockClass"] == "248"
    assert output_dict["clockAccuracy"] == "0xfe"
    assert output_dict["offsetScaledLogVariance"] == "0xffff"
    assert output_dict["priority2"] == "128"
    assert output_dict["clockIdentity"] == "507c6f.fffe.0b5a4d"
    assert output_dict["domainNumber"] == 0


def test_pmc_get_default_data_set_output():
    """
    Tests pmc get_default_data_set output

    """
    pmc_get_default_data_set_output = PMCGetDefaultDataSetOutput(pmc_output)
    pmc_get_default_data_set_object = pmc_get_default_data_set_output.get_pmc_get_default_data_set_object()

    assert pmc_get_default_data_set_object.get_two_step_flag() == 1
    assert pmc_get_default_data_set_object.get_slave_only() == 0
    assert pmc_get_default_data_set_object.get_number_ports() == 1
    assert pmc_get_default_data_set_object.get_priority1() == 128
    assert pmc_get_default_data_set_object.get_clock_class() == 248
    assert pmc_get_default_data_set_object.get_clock_accuracy() == "0xfe"
    assert pmc_get_default_data_set_object.get_offset_scaled_log_variance() == "0xffff"
    assert pmc_get_default_data_set_object.get_priority2() == 128
    assert pmc_get_default_data_set_object.get_clock_identity() == "507c6f.fffe.0b5a4d"
    assert pmc_get_default_data_set_object.get_domain_number() == 0


def test_pmc_get_parent_data_set_table_parser():
    """
    Tests the pmc table parser for get_parent_data_set output parser

    """
    pmc_table_parser = PMCTableParser(pmc_parent_data_set_output)
    output_dict_list = pmc_table_parser.get_output_values_dict()
    assert len(output_dict_list) == 1, "More than 1 parent data set was found"

    output_dict = output_dict_list[0]

    assert output_dict["parentPortIdentity"] == "507c6f.fffe.0b5a4d-0"
    assert output_dict["gm.ClockClass"] == "248"
    assert output_dict["gm.ClockAccuracy"] == "0xfe"
    assert output_dict["gm.OffsetScaledLogVariance"] == "0xffff"
    assert output_dict["grandmasterIdentity"] == "507c6f.fffe.0b5a4d"
    assert output_dict["grandmasterPriority1"] == "128"
    assert output_dict["grandmasterPriority2"] == "128"
    assert output_dict["observedParentClockPhaseChangeRate"] == "0x7fffffff"
    assert output_dict["observedParentOffsetScaledLogVariance"] == "0xffff"
    assert output_dict["parentStats"] == "0"


def test_pmc_get_parent_data_set_output():
    """
    Tests pmc get_parent_data_set output

    """
    pmc_get_parent_data_set_output = PMCGetParentDataSetOutput(pmc_parent_data_set_output)
    pmc_get_parent_data_set_object = pmc_get_parent_data_set_output.get_pmc_get_parent_data_set_object()

    assert pmc_get_parent_data_set_object.get_parent_port_identity() == "507c6f.fffe.0b5a4d-0"
    assert pmc_get_parent_data_set_object.get_gm_clock_class() == 248
    assert pmc_get_parent_data_set_object.get_gm_clock_accuracy() == "0xfe"
    assert pmc_get_parent_data_set_object.get_gm_offset_scaled_log_variance() == "0xffff"
    assert pmc_get_parent_data_set_object.get_grandmaster_identity() == "507c6f.fffe.0b5a4d"
    assert pmc_get_parent_data_set_object.get_grandmaster_priority1() == 128
    assert pmc_get_parent_data_set_object.get_grandmaster_priority2() == 128
    assert pmc_get_parent_data_set_object.get_observed_parent_clock_phase_change_rate() == "0x7fffffff"
    assert pmc_get_parent_data_set_object.get_observed_parent_offset_scaled_log_variance() == "0xffff"
    assert pmc_get_parent_data_set_object.get_parent_stats() == "0"


def test_pmc_get_current_data_set_output():
    """
    Tests pmc get_current_data_set output

    """
    pmc_current_data_set_output = PMCGetCurrentDataSetOutput(pmc_get_current_data_set_output)
    pmc_get_current_data_set_object = pmc_current_data_set_output.get_pmc_get_current_data_set_object()

    assert pmc_get_current_data_set_object.get_steps_removed() == 3
    assert pmc_get_current_data_set_object.get_mean_path_delay() == 2.5
    assert pmc_get_current_data_set_object.get_offset_from_master() == 1.3


def test_pmc_get_domain_output():
    """
    Tests pmc get domain output

    """
    pmc_domain_output = PMCGetDomainOutput(pmc_get_domain_output)
    pmc_get_domain_object = pmc_domain_output.get_pmc_get_domain_object()

    assert pmc_get_domain_object.get_domain_number() == 24


def test_pmc_get_grandmaster_settings_output():
    """
    Tests pmc get grandmaster settings output

    """
    pmc_grandmaster_settings_output = PMCGetGrandmasterSettingsNpOutput(pmc_get_grandmaster_settings_output)
    pmc_get_grandmaster_settings_object = pmc_grandmaster_settings_output.get_pmc_get_grandmaster_settings_np_object()

    assert pmc_get_grandmaster_settings_object.get_clock_accuracy() == "0x20"
    assert pmc_get_grandmaster_settings_object.get_offset_scaled_log_variance() == "0x4e5d"
    assert pmc_get_grandmaster_settings_object.get_clock_class() == 6
    assert pmc_get_grandmaster_settings_object.get_current_utc_offset() == 37
    assert pmc_get_grandmaster_settings_object.get_leap61() == 0
    assert pmc_get_grandmaster_settings_object.get_leap59() == 0
    assert pmc_get_grandmaster_settings_object.get_current_utc_off_set_valid() == 0
    assert pmc_get_grandmaster_settings_object.get_ptp_time_scale() == 1
    assert pmc_get_grandmaster_settings_object.get_time_traceable() == 1
    assert pmc_get_grandmaster_settings_object.get_frequency_traceable() == 1
    assert pmc_get_grandmaster_settings_object.get_time_source() == "0x20"


def test_pmc_get_time_properties_data_set_output():
    """
    Tests pmc get time properties data set output

    """
    pmc_time_properties_output = PMCGetTimePropertiesDataSetOutput(pmc_get_time_properties_data_set_output)
    pmc_time_properties_object = pmc_time_properties_output.get_pmc_get_time_properties_data_set_object()

    assert pmc_time_properties_object.get_current_utc_offset() == 37
    assert pmc_time_properties_object.get_leap61() == 0
    assert pmc_time_properties_object.get_leap59() == 0
    assert pmc_time_properties_object.get_current_utc_off_set_valid() == 0
    assert pmc_time_properties_object.get_ptp_time_scale() == 1
    assert pmc_time_properties_object.get_time_traceable() == 1
    assert pmc_time_properties_object.get_frequency_traceable() == 0
    assert pmc_time_properties_object.get_time_source() == "0x20"


def test_pmc_get_time_status_output():
    """
    Tests pmc get time properties data set output

    """
    pmc_time_status_output = PMCGetTimeStatusNpOutput(pmc_get_time_status_output)
    pmc_time_status_object = pmc_time_status_output.get_pmc_get_time_status_np_object()

    assert pmc_time_status_object.get_master_offset() == -62
    assert pmc_time_status_object.get_ingress_time() == 0
    assert pmc_time_status_object.get_cumulative_scaled_rate_offset() == "+0.000000000"
    assert pmc_time_status_object.get_scaled_last_gm_phase_change() == 0
    assert pmc_time_status_object.get_last_gm_phase_change() == "0x00000000000000000000.0000"
    assert pmc_time_status_object.get_gm_present() is False
    assert pmc_time_status_object.get_gm_identity() == "507c6f.fffe.0b5a4d"


def test_pmc_get_port_data_set_output():
    """
    Tests pmc get port data set data set output

    """
    pmc_port_data_set_output = PMCGetPortDataSetOutput(pmc_get_port_data_set_output)
    pmc_port_data_set_objects = pmc_port_data_set_output.get_pmc_get_port_data_set_objects()

    pmc_port_data_set_object_1 = pmc_port_data_set_objects[0]
    assert pmc_port_data_set_object_1.get_port_identity() == "b48351.fffe.0a37b0-1"
    assert pmc_port_data_set_object_1.get_port_state() == "SLAVE"
    assert pmc_port_data_set_object_1.get_log_min_delay_req_interval() == 0
    assert pmc_port_data_set_object_1.get_peer_mean_path_delay() == 0
    assert pmc_port_data_set_object_1.get_log_announce_interval() == 1
    assert pmc_port_data_set_object_1.get_announce_receipt_timeout() == 3
    assert pmc_port_data_set_object_1.get_log_sync_interval() == 0
    assert pmc_port_data_set_object_1.get_delay_mechanism() == 1
    assert pmc_port_data_set_object_1.get_log_min_p_delay_req_interval() == 0
    assert pmc_port_data_set_object_1.get_version_number() == 2

    pmc_port_data_set_object_2 = pmc_port_data_set_objects[1]
    assert pmc_port_data_set_object_2.get_port_identity() == "b48351.fffe.0a37b0-2"
    assert pmc_port_data_set_object_2.get_port_state() == "MASTER"
    assert pmc_port_data_set_object_2.get_log_min_delay_req_interval() == 0
    assert pmc_port_data_set_object_2.get_peer_mean_path_delay() == 0
    assert pmc_port_data_set_object_2.get_log_announce_interval() == 1
    assert pmc_port_data_set_object_2.get_announce_receipt_timeout() == 3
    assert pmc_port_data_set_object_2.get_log_sync_interval() == 0
    assert pmc_port_data_set_object_2.get_delay_mechanism() == 1
    assert pmc_port_data_set_object_2.get_log_min_p_delay_req_interval() == 0
    assert pmc_port_data_set_object_2.get_version_number() == 2
