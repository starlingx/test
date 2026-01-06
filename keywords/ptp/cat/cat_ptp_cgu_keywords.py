from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.ptp.cat.objects.ptp_cgu_component_output import PtpCguComponentOutput


class CatPtpCguKeywords(BaseKeyword):
    """
    Class for CAT PTP CGU Keywords.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor for CatPtpCguKeywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def cat_ptp_cgu(self, cgu_location: str) -> PtpCguComponentOutput:
        """
        Runs the command sudo cat <cgu_location> ex. /sys/kernel/debug/ice/0000:51:00.0/cgu.

        Args:
            cgu_location (str): the cgu location.

        Returns:
            PtpCguComponentOutput: the output of the cat ptp cgu command
        """
        output = self.ssh_connection.send_as_sudo(f"cat {cgu_location}")
        cat_ptp_cgu_component_output = PtpCguComponentOutput(output)
        return cat_ptp_cgu_component_output
