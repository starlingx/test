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
            if "Alarm ID" in value:
                alarm_list_object.set_alarm_id(value["Alarm ID"])
            if "Reason Text" in value:
                alarm_list_object.set_reason_text(value["Reason Text"])
            if "Entity ID" in value:
                alarm_list_object.set_entity_id(value["Entity ID"])
            if "Severity" in value:
                alarm_list_object.set_severity(value["Severity"])
            if "Time Stamp" in value:
                alarm_list_object.set_time_stamp(value["Time Stamp"])
            self.alarms.append(alarm_list_object)

    def get_alarms(self) -> list[AlarmListObject]:
        """
        Returns the list of alarms.

        Returns:
            list[AlarmListObject]: List of alarm objects.
        """
        return self.alarms

    def alarms_id(self) -> list[str]:
        """
        Return a list of alarm IDs from AlarmListObject instances.

        Returns:
            list[str]: List of alarm IDs.
        """
        return [alarm.get_alarm_id() for alarm in self.alarms]

    @staticmethod
    def is_new_alarm_id_since(alarm_ids_before: list[str], alarm_ids_after: list[str]) -> bool:
        """
        Check if there are new alarms compared to a previous state.

        Args:
            alarm_ids_before (list[str]): Alarm IDs before the test.
            alarm_ids_after (list[str]): Alarm IDs after the test.

        Returns:
            bool: True if new alarms are present, False if no new alarms.
        """
        alarm_ids_before_set = set(alarm_ids_before)
        alarm_ids_after_set = set(alarm_ids_after)

        new_alarms = list(alarm_ids_after_set - alarm_ids_before_set)

        return len(new_alarms) != 0
