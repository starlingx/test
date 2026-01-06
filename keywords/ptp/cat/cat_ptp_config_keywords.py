from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.ptp.cat.objects.cat_ptp_config_output import CATPtpConfigOutput


class CatPtpConfigKeywords(BaseKeyword):
    """Class for Cat Ptp Config Keywords"""

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor for CatPtpConfigKeywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def cat_ptp_config(self, config_file: str) -> CATPtpConfigOutput:
        """
        This command reads the contents of a PTP configuration file.

        Args:
            config_file (str): the ptp config file

        Returns:
            CATPtpConfigOutput: the output of the cat ptp config command
        """
        output = self.ssh_connection.send(f"cat {config_file}")
        self.validate_success_return_code(self.ssh_connection)
        cat_ptp_config_output = CATPtpConfigOutput(output)
        return cat_ptp_config_output
