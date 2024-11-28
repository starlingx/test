from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.dcmanager.objects.dcmanager_alarm_summary_object import DcManagerAlarmSummaryObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class DcManagerAlarmSummaryOutput:
    """
    This class parses the output of 'dcmanager alarm summary' command into a list of DcManagerAlarmSummaryObject
    """

    def __init__(self, dc_manager_alarm_summary_list_output):
        """
        Constructor

        Args:
            system_storage_backend_list_output: list of strings where each element is represented by a row in the
            'dcmanager alarm summary' command output.

            [
                "+-----------+-----------------+--------------+--------------+----------+----------+\n",
                "| NAME      | CRITICAL_ALARMS | MAJOR_ALARMS | MINOR_ALARMS | WARNINGS | STATUS   |\n",
                "+-----------+-----------------+--------------+--------------+----------+----------+\n",
                "| subcloud3 |               0 |            1 |            0 |        0 | degraded |\n",
                "| subcloud2 |               - |            - |            - |        - | disabled |\n",
                "| subcloud1 |               0 |            1 |            0 |        0 | degraded |\n",
                "+-----------+-----------------+--------------+--------------+----------+----------+\n"
            ]

        """
        self.dc_manager_alarm_summary_list: [DcManagerAlarmSummaryObject] = []
        system_table_parser = SystemTableParser(dc_manager_alarm_summary_list_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:

            if 'NAME' not in value:
                raise KeywordException(f"The output line {value} was not valid because it is missing the column 'NAME'.")

            dc_manager_alarm_summary_object = DcManagerAlarmSummaryObject(value['NAME'])

            if 'CRITICAL_ALARMS' in value:
                dc_manager_alarm_summary_object.set_critical_alarms(-1 if value['CRITICAL_ALARMS'] == "-" else int(value['CRITICAL_ALARMS']))

            if 'MAJOR_ALARMS' in value:
                dc_manager_alarm_summary_object.set_major_alarms(-1 if value['MAJOR_ALARMS'] == "-" else int(value['MAJOR_ALARMS']))

            if 'MINOR_ALARMS' in value:
                dc_manager_alarm_summary_object.set_minor_alarms(-1 if value['MINOR_ALARMS'] == "-" else int(value['MINOR_ALARMS']))

            if 'WARNINGS' in value:
                dc_manager_alarm_summary_object.set_warnings(-1 if value['WARNINGS'] == "-" else int(value['WARNINGS']))

            if 'STATUS' in value:
                dc_manager_alarm_summary_object.set_status(value['STATUS'])

            self.dc_manager_alarm_summary_list.append(dc_manager_alarm_summary_object)

    def get_dc_manager_summary_list(self) -> [DcManagerAlarmSummaryObject]:
        """
        Getter for the list of summarized alarms per subcloud. Each item in this list is a DcManagerAlarmSummaryObject,
        which represents a row in the table shown in the output of the 'dcmanager alarm summary' command.

        Returns:
            list[DcManagerAlarmSummaryObject]: list of DcManagerAlarmSummaryObject objects.

        """
        return self.dc_manager_alarm_summary_list
