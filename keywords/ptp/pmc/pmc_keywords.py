from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.ptp.pmc.objects.pmc_get_current_data_set_output import PMCGetCurrentDataSetOutput
from keywords.ptp.pmc.objects.pmc_get_default_data_set_output import PMCGetDefaultDataSetOutput
from keywords.ptp.pmc.objects.pmc_get_domain_output import PMCGetDomainOutput
from keywords.ptp.pmc.objects.pmc_get_grandmaster_settings_np_output import PMCGetGrandmasterSettingsNpOutput
from keywords.ptp.pmc.objects.pmc_get_parent_data_set_output import PMCGetParentDataSetOutput
from keywords.ptp.pmc.objects.pmc_get_port_data_set_output import PMCGetPortDataSetOutput
from keywords.ptp.pmc.objects.pmc_get_time_properties_data_set_output import PMCGetTimePropertiesDataSetOutput
from keywords.ptp.pmc.objects.pmc_get_time_status_np_output import PMCGetTimeStatusNpOutput


class PMCKeywords(BaseKeyword):
    """
    Class for PMC Keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def pmc_get_time_status_np(self, config_file: str, socket_file: str, unicast: bool = True, boundry_clock: int = 0) -> PMCGetTimeStatusNpOutput:
        """
        Gets the TIME_STATUS_NP

        Args:
            config_file (str): the config file
            socket_file (str): the socket file
            unicast (bool): true to use unicast
            boundry_clock (int): the boundry clock

        Returns:
            PMCGetTimeStatusNpOutput: the status output

        Example: PMCKeywords(ssh_connection).pmc_get_time_status_np('/etc/linuxptp/ptpinstance/ptp4l-ptp5.conf', ' /var/run/ptp4l-ptp5')

        """
        cmd = f"pmc {'-u' if unicast else ''} -b {boundry_clock} -f {config_file} -s {socket_file} 'GET TIME_STATUS_NP'"

        output = self.ssh_connection.send_as_sudo(cmd)
        pmc_get_time_status_np_output = PMCGetTimeStatusNpOutput(output)
        return pmc_get_time_status_np_output

    def pmc_get_current_data_set(self, config_file: str, socket_file: str, unicast: bool = True, boundry_clock: int = 0) -> PMCGetCurrentDataSetOutput:
        """
        Gets the CURRENT_DATA_SET

        Args:
            config_file (str): the config file
            socket_file (str): the socket file
            unicast (bool): true to use unicast
            boundry_clock (int): the boundry clock

        Returns:
            PMCGetCurrentDataSetOutput: the output

        Example: PMCKeywords(ssh_connection).pmc_get_current_data_set('/etc/linuxptp/ptpinstance/ptp4l-ptp5.conf', ' /var/run/ptp4l-ptp5')

        """
        cmd = f"pmc {'-u' if unicast else ''} -b {boundry_clock} -f {config_file} -s {socket_file} 'GET CURRENT_DATA_SET'"

        output = self.ssh_connection.send_as_sudo(cmd)
        pmc_get_current_data_set_output = PMCGetCurrentDataSetOutput(output)
        return pmc_get_current_data_set_output

    def pmc_get_port_data_set(self, config_file: str, socket_file: str, unicast: bool = True, boundry_clock: int = 0) -> PMCGetPortDataSetOutput:
        """
        Gets the port data set

        Args:
            config_file (str): the config file
            socket_file (str): the socket file
            unicast (bool): true to use unicast
            boundry_clock (int): the boundry clock

        Returns:
            PMCGetPortDataSetOutput: the port data set output

        Example: PMCKeywords(ssh_connection).pmc_get_port_data_set('/etc/linuxptp/ptpinstance/ptp4l-ptp5.conf', ' /var/run/ptp4l-ptp5')

        """
        cmd = f"pmc {'-u' if unicast else ''} -b {boundry_clock} -f {config_file} -s {socket_file} 'GET PORT_DATA_SET'"

        output = self.ssh_connection.send_as_sudo(cmd)
        pmc_get_port_data_set_output = PMCGetPortDataSetOutput(output)
        return pmc_get_port_data_set_output

    def pmc_set_grandmaster_settings_np(self, config_file: str, socket_file: str, clock_class: int, time_traceable: int) -> PMCGetGrandmasterSettingsNpOutput:
        """
        SET GRANDMASTER_SETTINGS_NP

        Args:
            config_file(str) : the config file
            socket_file(str) : the socket file
            clock_class(int) : clockClass of ptp
            time_traceable(int) : timeTraceable of ptp

        Returns:
            PMCGetGrandmasterSettingsNpOutput: the grandmaster settings output

        Example: PMCKeywords(ssh_connection).pmc_set_grandmaster_settings_np('/etc/linuxptp/ptpinstance/ptp4l-ptp5.conf', '/var/run/ptp4l-ptp5', 7, 1)

        """
        cmd = f"pmc -u -b 0 -f {config_file} -s {socket_file} 'SET GRANDMASTER_SETTINGS_NP clockClass {clock_class} clockAccuracy 0xfe offsetScaledLogVariance 0xffff currentUtcOffset 37 leap61 0 leap59 0 currentUtcOffsetValid 0 ptpTimescale 1 timeTraceable {time_traceable} frequencyTraceable 0 timeSource 0xa0'"

        output = self.ssh_connection.send_as_sudo(cmd)
        pmc_set_grandmaster_settings_np_output = PMCGetGrandmasterSettingsNpOutput(output)
        return pmc_set_grandmaster_settings_np_output

    def pmc_get_grandmaster_settings_np(self, config_file: str, socket_file: str, unicast: bool = True, boundry_clock: int = 0) -> PMCGetGrandmasterSettingsNpOutput:
        """
        Gets the grandmaster_settings_np

        Args:
            config_file(str) : the config file
            socket_file(str) : the socket file
            unicast(bool) : true to use unicast
            boundry_clock(int) : the boundry clock

        Returns:
            PMCGetGrandmasterSettingsNpOutput: the grandmaster settings output

        Example: PMCKeywords(ssh_connection).pmc_get_grandmaster_settings_np('/etc/linuxptp/ptpinstance/ptp4l-ptp5.conf', ' /var/run/ptp4l-ptp5')

        """
        cmd = f"pmc {'-u' if unicast else ''} -b {boundry_clock} -f {config_file} -s {socket_file} 'GET GRANDMASTER_SETTINGS_NP'"

        output = self.ssh_connection.send_as_sudo(cmd)
        pmc_get_grandmaster_settings_np_output = PMCGetGrandmasterSettingsNpOutput(output)
        return pmc_get_grandmaster_settings_np_output

    def pmc_get_time_properties_data_set(self, config_file: str, socket_file: str, unicast: bool = True, boundry_clock: int = 0) -> PMCGetTimePropertiesDataSetOutput:
        """
        Gets the time_properties_data_set_object

        Args:
            config_file(str) : the config file
            socket_file(str) : the socket file
            unicast(bool) : true to use unicast
            boundry_clock(int) : the boundry clock

        Returns:
            PMCGetTimePropertiesDataSetOutput: the time properties data set output

        Example: PMCKeywords(ssh_connection).pmc_get_time_properties_data_set('/etc/linuxptp/ptpinstance/ptp4l-ptp5.conf', ' /var/run/ptp4l-ptp5')

        """
        cmd = f"pmc {'-u' if unicast else ''} -b {boundry_clock} -f {config_file} -s {socket_file} 'GET TIME_PROPERTIES_DATA_SET'"

        output = self.ssh_connection.send_as_sudo(cmd)
        pmc_get_time_properties_data_set_output = PMCGetTimePropertiesDataSetOutput(output)
        return pmc_get_time_properties_data_set_output

    def pmc_get_default_data_set(self, config_file: str, socket_file: str, unicast: bool = True, boundry_clock: int = 0) -> PMCGetDefaultDataSetOutput:
        """
        Gets the default data set

        Args:
            config_file (str): the config file
            socket_file (str): the socket file
            unicast (bool): true to use unicast
            boundry_clock (int): the boundry clock

        Returns:
            PMCGetDefaultDataSetOutput: the default dataset output

        Example: PMCKeywords(ssh_connection).pmc_get_default_data_set('/etc/linuxptp/ptpinstance/ptp4l-ptp5.conf', ' /var/run/ptp4l-ptp5')

        """
        cmd = f"pmc {'-u' if unicast else ''} -b {boundry_clock} -f {config_file} -s {socket_file} 'GET DEFAULT_DATA_SET'"

        output = self.ssh_connection.send_as_sudo(cmd)
        pmc_get_default_data_set_output = PMCGetDefaultDataSetOutput(output)
        return pmc_get_default_data_set_output

    def pmc_get_domain(self, config_file: str, socket_file: str, unicast: bool = True, boundry_clock: int = 0) -> PMCGetDomainOutput:
        """
        Gets the domain

        Args:
            config_file (str): the config file
            socket_file (str): the socket file
            unicast (bool): true to use unicast
            boundry_clock (int): the boundry clock

        Returns:
            PMCGetDomainOutput: the get domain output

        Example: PMCKeywords(ssh_connection).pmc_get_domain('/etc/linuxptp/ptpinstance/ptp4l-ptp5.conf', ' /var/run/ptp4l-ptp5')

        """
        cmd = f"pmc {'-u' if unicast else ''} -b {boundry_clock} -f {config_file} -s {socket_file} 'GET DOMAIN'"

        output = self.ssh_connection.send_as_sudo(cmd)
        pmc_get_domain_output = PMCGetDomainOutput(output)
        return pmc_get_domain_output

    def pmc_get_parent_data_set(self, config_file: str, socket_file: str, unicast: bool = True, boundry_clock: int = 0) -> PMCGetParentDataSetOutput:
        """
        Gets the parent data set

        Args:
            config_file (str): the config file
            socket_file (str): the socket file
            unicast (bool): true to use unicast
            boundry_clock (int): the boundry clock

        Returns:
            PMCGetParentDataSetOutput: the parent data set output

        Example: PMCKeywords(ssh_connection).pmc_get_parent_data_set('/etc/linuxptp/ptpinstance/ptp4l-ptp5.conf', '/var/run/ptp4l-ptp5')

        """
        cmd = f"pmc {'-u' if unicast else ''} -b {boundry_clock} -f {config_file} -s {socket_file} 'GET PARENT_DATA_SET'"

        output = self.ssh_connection.send_as_sudo(cmd)
        pmc_get_parent_data_set_output = PMCGetParentDataSetOutput(output)
        return pmc_get_parent_data_set_output
