from config.configuration_manager import ConfigurationManager
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.addrpool.object.system_addrpool_list_output import SystemAddrpoolListOutput


class SystemAddrpoolListKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system addrpool' commands.
    """
    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection


    def get_system_addrpool_list(self) -> SystemAddrpoolListOutput:
        """
        Gets a SystemAddrpoolOutput object related to the execution of the 'system addrpool-list' command.

        Returns:
             SystemAddrpoolListOutput: an instance of the SystemAddrpoolOutput object representing the
             address pool of IPs on the host, as a result of the execution of the 'system addrpool-list' command.
        """

        output = self.ssh_connection.send(source_openrc('system addrpool-list'))
        self.validate_success_return_code(self.ssh_connection)
        
        system_addrpool_list_output = SystemAddrpoolListOutput(output)
        
        return system_addrpool_list_output
    
    def get_management_floating_address(self) -> str:
        """
        Retrieves the floating address for the addrpool with name 'management'.

        Returns:
            The floating address for the name with management field.
        """
        return self.get_system_addrpool_list().get_floating_address_by_name("management")

    def get_management_gateway_address(self) -> str:
        """
        Retrieves the gateway address for the addrpool with name 'management'.

        Returns:
            The gateway address for the name with management field.
        """
        return self.get_system_addrpool_list().get_gateway_address_by_name("management")

    def get_admin_gateway_address(self) -> str:
        """
        Retrieves the gateway address for the addrpool with name 'admin'.

        Args:
            ipv4 (bool): If ipv4 is True, searches for <network>-ipv4,
            if not, searches for <network>-ipv6.

        Returns:
            The gateway address for the name with management field.
        """
        lab_config = ConfigurationManager.get_lab_config()
        if lab_config.is_ipv6():
            net_type = "ipv6"
        else:
            net_type = "ipv4"
        return self.get_system_addrpool_list().get_gateway_address_by_name(f"admin-{net_type}")
