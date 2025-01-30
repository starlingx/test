from keywords.ptp.pmc.objects.pmc_get_default_data_set_output import PMCGetDefaultDataSetOutput
from keywords.ptp.pmc.objects.pmc_get_parent_data_set_output import PMCGetParentDataSetOutput
from keywords.ptp.pmc.pmc_table_parser import PMCTableParser

pmc_output = [
    'sending: GET DEFAULT_DATA_SET\n',
    '   507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT DEFAULT_DATA_SET\n',
    '       twoStepFlag            1\n',
    '       slaveOnly              0\n',
    '       numberPorts            1\n',
    '       priority1              128\n',
    '       clockClass             248\n',
    '       clockAccuracy          0xfe\n',
    '       offsetScaledLogVariance 0xffff\n',
    '       priority2              128\n',
    '       clockIdentity          507c6f.fffe.0b5a4d\n',
    '       domainNumber           0.\n',
    'sysadmin@controller-0:~$\n',
]

pmc_parent_data_set_output = [
    'sending: GET PARENT_DATA_SET\n',
    '   507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT PARENT_DATA_SET\n',
    '       parentPortIdentity                    507c6f.fffe.0b5a4d-0\n',
    '       parentStats                           0\n',
    '       observedParentOffsetScaledLogVariance 0xffff\n',
    '       observedParentClockPhaseChangeRate    0x7fffffff\n',
    '       grandmasterPriority1                  128\n',
    '       gm.ClockClass                         248\n',
    '       gm.ClockAccuracy                      0xfe\n',
    '       gm.OffsetScaledLogVariance            0xffff\n',
    '       grandmasterPriority2                  128\n',
    '       grandmasterIdentity                   507c6f.fffe.0b5a4d\n',
    'sysadmin@controller-0:~$\n',
]


def test_pmc_get_default_data_set_table_parser():
    """
    Tests the pmc table parser for get_default_data_set output parser
    Returns:

    """
    pmc_table_parser = PMCTableParser(pmc_output)
    output_dict = pmc_table_parser.get_output_values_dict()

    assert output_dict['twoStepFlag'] == '1'
    assert output_dict['slaveOnly'] == '0'
    assert output_dict['numberPorts'] == '1'
    assert output_dict['priority1'] == '128'
    assert output_dict['clockClass'] == '248'
    assert output_dict['clockAccuracy'] == '0xfe'
    assert output_dict['offsetScaledLogVariance'] == '0xffff'
    assert output_dict['priority2'] == '128'
    assert output_dict['clockIdentity'] == '507c6f.fffe.0b5a4d'
    assert output_dict['domainNumber'] == '0.'


def test_pmc_get_default_data_set_output():
    """
        Tests pmc get_default_data_set output
        Returns:

        """
    pmc_get_default_data_set_output = PMCGetDefaultDataSetOutput(pmc_output)
    pmc_get_default_data_set_object = pmc_get_default_data_set_output.get_pmc_get_default_data_set_object()

    assert pmc_get_default_data_set_object.get_two_step_flag() == 1
    assert pmc_get_default_data_set_object.get_slave_only() == 0
    assert pmc_get_default_data_set_object.get_number_ports() == 1
    assert pmc_get_default_data_set_object.get_priority1() == 128
    assert pmc_get_default_data_set_object.get_clock_class() == 248
    assert pmc_get_default_data_set_object.get_clock_accuracy() == '0xfe'
    assert pmc_get_default_data_set_object.get_offset_scaled_log_variance() == '0xffff'
    assert pmc_get_default_data_set_object.get_priority2() == 128
    assert pmc_get_default_data_set_object.get_clock_identity() == '507c6f.fffe.0b5a4d'
    assert pmc_get_default_data_set_object.get_domain_number() == '0.'


def test_pmc_get_parent_data_set_table_parser():
    """
    Tests the pmc table parser for get_parent_data_set output parser
    Returns:

    """
    pmc_table_parser = PMCTableParser(pmc_parent_data_set_output)
    output_dict = pmc_table_parser.get_output_values_dict()

    assert output_dict['parentPortIdentity'] == '507c6f.fffe.0b5a4d-0'
    assert output_dict['gm.ClockClass'] == '248'
    assert output_dict['gm.ClockAccuracy'] == '0xfe'
    assert output_dict['gm.OffsetScaledLogVariance'] == '0xffff'
    assert output_dict['grandmasterIdentity'] == '507c6f.fffe.0b5a4d'
    assert output_dict['grandmasterPriority1'] == '128'
    assert output_dict['grandmasterPriority2'] == '128'
    assert output_dict['observedParentClockPhaseChangeRate'] == '0x7fffffff'
    assert output_dict['observedParentOffsetScaledLogVariance'] == '0xffff'
    assert output_dict['parentStats'] == '0'


def test_pmc_get_parent_data_set_output():
    """
        Tests pmc get_parent_data_set output
        Returns:

        """
    pmc_get_parent_data_set_output = PMCGetParentDataSetOutput(pmc_parent_data_set_output)
    pmc_get_parent_data_set_object = pmc_get_parent_data_set_output.get_pmc_get_parent_data_set_object()

    assert pmc_get_parent_data_set_object.get_parent_port_identity() == '507c6f.fffe.0b5a4d-0'
    assert pmc_get_parent_data_set_object.get_gm_clock_class() == 248
    assert pmc_get_parent_data_set_object.get_gm_clock_accuracy() == '0xfe'
    assert pmc_get_parent_data_set_object.get_gm_offset_scaled_log_variance() == '0xffff'
    assert pmc_get_parent_data_set_object.get_grandmaster_identity() == '507c6f.fffe.0b5a4d'
    assert pmc_get_parent_data_set_object.get_grandmaster_priority1() == 128
    assert pmc_get_parent_data_set_object.get_grandmaster_priority2() == 128
    assert pmc_get_parent_data_set_object.get_observed_parent_clock_phase_change_rate() == '0x7fffffff'
    assert pmc_get_parent_data_set_object.get_observed_parent_offset_scaled_log_variance() == '0xffff'
    assert pmc_get_parent_data_set_object.get_parent_stats() == '0'
