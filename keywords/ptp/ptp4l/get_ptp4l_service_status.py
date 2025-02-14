from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.linux.systemctl.systemctl_status_keywords import SystemCTLStatusKeywords
from keywords.ptp.ptp4l.objects.ptp4l_status_output import PTP4LStatusOutput


class GetPtp4lServiceStatusKeywords(BaseKeyword):
    """
    Get PTP4L Service Status Keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def get_systemctl_ptp4l_status(self) -> PTP4LStatusOutput:
        """
        Getter for systemctl ptp4l status output
        Returns:

        """
        output = SystemCTLStatusKeywords(self.ssh_connection).get_status('ptp4l@*')
        ptp4l_status_output = PTP4LStatusOutput(output)
        return ptp4l_status_output

