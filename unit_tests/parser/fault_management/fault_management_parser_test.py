from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_output import AlarmListOutput
from keywords.cloud_platform.fault_management.fault_management_table_parser import FaultManagementTableParser

alarm_output = [
    '+----------+---------------------------+------------------------------------+----------+----------------------------+\n',
    '| Alarm ID | Reason Text               | Entity ID                          | Severity | Time Stamp                 |\n',
    '+----------+---------------------------+------------------------------------+----------+----------------------------+\n',
    '| 750.002  | Application Apply Failure | k8s_application=sriov-fec-operator | major    | 2024-05-07T11:20:52.071247 |\n',
    '+----------+---------------------------+------------------------------------+----------+----------------------------+\n',
]

alarm_output_error = [
    '+----------+---------------------------+------------------------------------+----------+----------------------------+\n',
    '| Alarm ID | Reason Text               | Entity ID                          | Severity | \n',
    '+----------+---------------------------+------------------------------------+----------+----------------------------+\n',
    '| 750.002  | Application Apply Failure | k8s_application=sriov-fec-operator | major    | 2024-05-07T11:20:52.071247 |\n',
    '+----------+---------------------------+------------------------------------+----------+----------------------------+\n',
]


def test_fault_management_parser():
    """
    Tests the fault management parser
    Returns:

    """
    fault_management_parser = FaultManagementTableParser(alarm_output)
    output_list = fault_management_parser.get_output_values_list()

    assert len(output_list) == 1
    output = output_list[0]
    assert output['Alarm ID'] == '750.002'
    assert output['Reason Text'] == 'Application Apply Failure'
    assert output['Entity ID'] == 'k8s_application=sriov-fec-operator'
    assert output['Severity'] == 'major'
    assert output['Time Stamp'] == '2024-05-07T11:20:52.071247'


def test_fault_management_table_parser_error():
    """
    Tests the fault management parser with an error in the input
    Returns:

    """
    try:
        configuration_locations_manager = ConfigurationFileLocationsManager()
        ConfigurationManager.load_configs(configuration_locations_manager)
        FaultManagementTableParser(alarm_output_error).get_output_values_list()
        assert False, "There should be an exception when parsing the output."
    except KeywordException as e:
        assert e.args[0] == 'Number of headers and values do not match'


def test_alarm_list_output():
    """
    Tests the alarm_list output parser
    Returns:

    """
    alarms_output = AlarmListOutput(alarm_output)
    alarms = alarms_output.get_alarms()

    assert len(alarms) == 1

    alarm = alarms[0]
    assert alarm.get_alarm_id() == '750.002'
    assert alarm.get_reason_text() == 'Application Apply Failure'
    assert alarm.get_entity_id() == 'k8s_application=sriov-fec-operator'
    assert alarm.get_severity() == 'major'
    assert alarm.get_time_stamp() == '2024-05-07T11:20:52.071247'


def test_alarm_list_error():
    """
    Tests the alarm_list output parser with an error in the input
    Returns:

    """
    try:
        configuration_locations_manager = ConfigurationFileLocationsManager()
        ConfigurationManager.load_configs(configuration_locations_manager)
        AlarmListOutput(alarm_output_error).get_alarms()
        assert False, "There should be an exception when we parse the output."
    except KeywordException as e:
        assert e.args[0] == 'Number of headers and values do not match'
