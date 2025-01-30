from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.ptp.pmc.objects.pmc_get_default_data_set_output import PMCGetDefaultDataSetOutput
from keywords.ptp.pmc.objects.pmc_get_parent_data_set_output import PMCGetParentDataSetOutput


class PMCKeywords(BaseKeyword):
    """
    Class for PMC Keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def pmc_get_default_data_set(self, config_file: str, socket_file: str, unicast: bool = True, boundry_clock: int = 0) -> PMCGetDefaultDataSetOutput:
        """
        Gets the default data et
        Args:
            config_file (): the config file
            socket_file (): the socket file
            unicast (): true to use unicast
            boundry_clock (): the boundry clock

        Example: PMCKeywords(ssh_connection).pmc_get_default_data_set('/etc/linuxptp/ptpinstance/ptp4l-ptp5.conf', ' /var/run/ptp4l-ptp5')

        """
        cmd = f"pmc {'-u' if unicast else ''} -b {boundry_clock} -f {config_file} -s {socket_file} 'GET DEFAULT_DATA_SET'"

        output = self.ssh_connection.send_as_sudo(cmd)
        pmc_get_default_data_set_output = PMCGetDefaultDataSetOutput(output)
        return pmc_get_default_data_set_output

    def pmc_get_parent_data_set(self, config_file: str, socket_file: str, unicast: bool = True, boundry_clock: int = 0) -> PMCGetParentDataSetOutput:
        """
        Gets the parent data set
        Args:
            config_file (): the config file
            socket_file (): the socket file
            unicast (): true to use unicast
            boundry_clock (): the boundry clock

        Example: PMCKeywords(ssh_connection).pmc_get_parent_data_set('/etc/linuxptp/ptpinstance/ptp4l-ptp5.conf', '/var/run/ptp4l-ptp5')

        """
        cmd = f"pmc {'-u' if unicast else ''} -b {boundry_clock} -f {config_file} -s {socket_file} 'GET PARENT_DATA_SET'"

        output = self.ssh_connection.send_as_sudo(cmd)
        pmc_get_parent_data_set_output = PMCGetParentDataSetOutput(output)
        return pmc_get_parent_data_set_output
