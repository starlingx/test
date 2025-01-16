from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.system.show.objects.system_show_output import SystemShowOutput


class SystemModifyKeywords(BaseKeyword):

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def system_modify_timezone(self, timezone: str) -> SystemShowOutput:
        """
        Runs system command system modify --timezone
        """
        output = self.ssh_connection.send(source_openrc(f'system modify --timezone="{timezone}"'))
        self.validate_success_return_code(self.ssh_connection)
        system_show_output = SystemShowOutput(output)

        # config alarms will appear, wait for them to be gone
        alarm_list_object = AlarmListObject()
        alarm_list_object.set_alarm_id('250.001')
        AlarmListKeywords(self.ssh_connection).wait_for_alarms_cleared([alarm_list_object])

        return system_show_output
