import ipaddress
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.addrpool.object.system_addrpool_list_output import SystemAddrpoolListOutput


class SystemAddrpoolListKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system addrpool' commands.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): ssh for active controller.
        """
        self.ssh_connection = ssh_connection

    def get_system_addrpool_list(self) -> SystemAddrpoolListOutput:
        """
        Gets a SystemAddrpoolOutput object related to the execution of the 'system addrpool-list' command.

        Returns:
             SystemAddrpoolListOutput: an instance of the SystemAddrpoolOutput object representing the
             address pool of IPs on the host, as a result of the execution of the 'system addrpool-list' command.
        """
        output = self.ssh_connection.send(source_openrc("system addrpool-list"))
        self.validate_success_return_code(self.ssh_connection)
        system_addrpool_list_output = SystemAddrpoolListOutput(output)
        return system_addrpool_list_output

    def modify_management_addrpool(self, network: str, prefix: str, floating_address: str,
                                 controller0_address: str, controller1_address: str, 
                                 gateway_address: str, ranges: str) -> None:
        """
        Modify the management-ipv4 address pool with new network configuration.
        
        Args:
            network (str): Network address (e.g., '192.168.202.0')
            prefix (str): Network prefix (e.g., '24')
            floating_address (str): Floating IP address (e.g., '192.168.202.2')
            controller0_address (str): Controller-0 IP address (e.g., '192.168.202.3')
            controller1_address (str): Controller-1 IP address (e.g., '192.168.202.4')
            gateway_address (str): Gateway IP address (e.g., '192.168.202.1')
            ranges (str): IP address ranges (e.g., '192.168.202.2-192.168.202.50')
        """
        # Get UUID of management-ipv4 addrpool
        uuid_cmd = "system addrpool-list | grep management-ipv4 | awk '{print $2}'"
        uuid_output = self.ssh_connection.send(source_openrc(uuid_cmd))
        self.validate_success_return_code(self.ssh_connection)
        uuid = uuid_output.strip()
        
        # Modify the addrpool
        modify_cmd = f"system addrpool-modify {uuid} " \
                    f"--network {network} " \
                    f"--prefix {prefix} " \
                    f"--floating-address {floating_address} " \
                    f"--controller0-address {controller0_address} " \
                    f"--controller1-address {controller1_address} " \
                    f"--gateway-address {gateway_address} " \
                    f"--ranges {ranges}"
        
    def add_addrpool_from_bootstrap_yaml_values(self, admin_start_address: str, admin_gateway_address: str,
                                     admin_subnet: str, admin_subnet_prefix: str, is_ipv6: bool = False) -> None:
        """
        Add admin address pool using values from YAML configuration
        
        Args:
            admin_start_address (str): Admin start address from YAML
            admin_gateway_address (str): Admin gateway address from YAML  
            admin_subnet (str): Admin subnet from YAML
            admin_subnet_prefix (str): Admin subnet prefix from YAML
            is_ipv6 (bool): Whether this is IPv6 configuration
        """
        # Calculate controller addresses from admin range
        start_ip = ipaddress.ip_address(admin_start_address)
        controller0_address = str(start_ip + 1)
        controller1_address = str(start_ip + 2)
        
        # Determine pool name based on IP version
        pool_name = "admin-ipv6" if is_ipv6 else "admin-ipv4"
        
        cmd = f"system addrpool-add --floating-address {admin_start_address} " \
              f"--controller0-address {controller0_address} " \
              f"--controller1-address {controller1_address} " \
              f"--gateway-address {admin_gateway_address} {pool_name} {admin_subnet} {admin_subnet_prefix}"

        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

