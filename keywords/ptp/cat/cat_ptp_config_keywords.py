from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.ptp.cat.objects.cat_ptp_config_output import CATPtpConfigOutput


class CatPtpConfigKeywords(BaseKeyword):
    """
    Class for Cat Ptp Config Keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def cat_ptp_config(self, config_file: str) -> CATPtpConfigOutput:
        """
        Run cat cpt config command
        Args:
            config_file (): the ptp config file

        Returns: CatPtpConfigOutput

        """
        output = self.ssh_connection.send(f'cat {config_file}')
        self.validate_success_return_code(self.ssh_connection)
        cat_ptp_config_output = CATPtpConfigOutput(output)
        return cat_ptp_config_output

