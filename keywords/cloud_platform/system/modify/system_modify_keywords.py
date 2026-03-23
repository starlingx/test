from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.system.show.objects.system_show_output import SystemShowOutput


class SystemModifyKeywords(BaseKeyword):
    """Keywords for the 'system modify' CLI command."""

    def __init__(self, ssh_connection):
        """Constructor.

        Args:
            ssh_connection: SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def system_modify_timezone(self, timezone: str) -> SystemShowOutput:
        """Run system modify --timezone.

        Args:
            timezone (str): Timezone value to set.

        Returns:
            SystemShowOutput: The output of the system modify command.
        """
        output = self.ssh_connection.send(source_openrc(f'system modify --timezone="{timezone}"'))
        self.validate_success_return_code(self.ssh_connection)
        system_show_output = SystemShowOutput(output)

        # config alarms will appear, wait for them to be gone
        alarm_list_object = AlarmListObject()
        alarm_list_object.set_alarm_id('250.001')
        AlarmListKeywords(self.ssh_connection).wait_for_alarms_cleared([alarm_list_object])

        return system_show_output

    def system_modify_https_enabled(self, https_enabled: bool) -> SystemShowOutput:
        """Run system modify --https-enabled.

        Args:
            https_enabled (bool): Boolean value to enable or disable https.

        Returns:
            SystemShowOutput: The output of the system modify command.
        """
        output = self.ssh_connection.send(source_openrc(f"system modify -p {https_enabled}"))
        self.validate_success_return_code(self.ssh_connection)
        return SystemShowOutput(output)

    def system_modify_latitude_longitude(self, latitude: float, longitude: float) -> SystemShowOutput:
        """Run system modify --latitude <lat> --longitude <long>.

        Args:
            latitude (float): Latitude value to set.
            longitude (float): Longitude value to set.

        Returns:
            SystemShowOutput: The output of the system modify command.
        """
        output = self.ssh_connection.send(source_openrc(f"system modify --latitude {latitude} --longitude {longitude}"))
        self.validate_success_return_code(self.ssh_connection)
        return SystemShowOutput(output)
