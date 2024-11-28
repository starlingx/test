from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_output import AlarmListOutput


class AlarmListKeywords(BaseKeyword):
    """
    Class for alarm list keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def alarm_list(self) -> [AlarmListObject]:
        """
        Keyword to get all alarms
        Args:

        Returns: the list of alarms

        """
        output = self.ssh_connection.send(source_openrc('fm alarm-list --nowrap'))
        self.validate_success_return_code(self.ssh_connection)
        alarms = AlarmListOutput(output)

        return alarms.get_alarms()
