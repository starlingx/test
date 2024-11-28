from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_alarm_summary_output import DcManagerAlarmSummaryOutput


class DcManagerAlarmSummaryKeywords(BaseKeyword):
    """
    Class for DcManager Alarm Summary Keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): the ssh connection to the dc cloud.
        """
        self.ssh_connection = ssh_connection

    def get_alarm_summary_list(self):
        """
        Getter for the list of summarized alarms per subcloud.

        Returns:
            list[DcManagerAlarmSummaryObject]: list of DcManagerAlarmSummaryObject objects. Each object represents a row
            in the table shown in the output of the 'dcmanager alarm summary' command.

        """
        output = self.ssh_connection.send(source_openrc('dcmanager alarm summary'))
        self.validate_success_return_code(self.ssh_connection)
        alarms = DcManagerAlarmSummaryOutput(output)

        return alarms.get_dc_manager_summary_list()
