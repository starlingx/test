from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.fault_management.fault_management_table_parser import FaultManagementTableParser


class AlarmListOutput:
    """
    Class for Alarm List Output
    """

    def __init__(self, alarm_list_output):
        self.alarms: [AlarmListObject] = []
        fault_management_table_parser = FaultManagementTableParser(alarm_list_output)
        output_values = fault_management_table_parser.get_output_values_list()

        for value in output_values:
            alarm_list_object = AlarmListObject()
            if 'Alarm ID' in value:
                alarm_list_object.set_alarm_id(value['Alarm ID'])
            if 'Reason Text' in value:
                alarm_list_object.set_reason_text(value['Reason Text'])
            if 'Entity ID' in value:
                alarm_list_object.set_entity_id(value['Entity ID'])
            if 'Severity' in value:
                alarm_list_object.set_severity(value['Severity'])
            if 'Time Stamp' in value:
                alarm_list_object.set_time_stamp(value['Time Stamp'])
            self.alarms.append(alarm_list_object)

    def get_alarms(self) -> [AlarmListObject]:
        """
        Returns the list of alarms
        Returns:

        """
        return self.alarms
