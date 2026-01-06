from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.ptp.cat.objects.clock_conf_output import ClockConfOutput


class CatClockConfKeywords(BaseKeyword):
    """
    Class for CAT Clock Conf Keywords.
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def cat_clock_conf(self, clock_conf_location: str) -> ClockConfOutput:
        """
        Runs the command sudo cat <clock_conf_location> ex. /etc/linuxptp/ptpinstance/clock-conf.conf.

        Args:
            clock_conf_location (str): the clock conf location.

        Returns:
            ClockConfOutput: the ClockConfOutput.

        """
        output = self.ssh_connection.send_as_sudo(f"cat {clock_conf_location}")
        clock_conf_output = ClockConfOutput(output)
        return clock_conf_output
