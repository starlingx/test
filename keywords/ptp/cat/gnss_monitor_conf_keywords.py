from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.ptp.cat.objects.gnss_monitor_conf_output import GnssMonitorConfOutput


class GnssMonitorConfKeywords(BaseKeyword):
    """
    Class for GNSS Monitor Conf Keywords.
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def cat_gnss_monitor_conf(self, gnss_monitor_conf_location: str) -> GnssMonitorConfOutput:
        """
        Runs the command sudo cat <gnss_monitor_conf_location> ex. /etc/linuxptp/ptpinstance/gnss-monitor-ptp.conf.

        Args:
            gnss_monitor_conf_location (str): the GNSS monitor conf location.

        Returns:
            GnssMonitorConfOutput: the GnssMonitorConfOutput.

        """
        output = self.ssh_connection.send_as_sudo(f"cat {gnss_monitor_conf_location}")
        gnss_monitor_conf_output = GnssMonitorConfOutput(output)
        return gnss_monitor_conf_output
