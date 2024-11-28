from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.networking.sriov.object.sriov_config_object import SriovConfigObject
from keywords.cloud_platform.system.host.system_host_if_keywords import SystemHostInterfaceKeywords
from keywords.cloud_platform.system.interface.system_interface_datanetwork_keywords import SystemInterfaceDatanetworkKeywords


class GetSriovConfigKeywords(BaseKeyword):
    """
    Get Sriov Config Keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def get_sriov_configs_for_host(self, hostname: str) -> [SriovConfigObject]:
        """
        Gets the sriov configs for the given host
        Args:
            hostname ():

        Returns:

        """
        # get all interfaces for the given host
        interfaces = SystemHostInterfaceKeywords(self.ssh_connection).get_system_host_interface_list(hostname)

        # get the sriov interfaces
        if not interfaces:
            raise KeywordException(f"No interfaces found for host {hostname}")

        sriov_interfaces = interfaces.get_interfaces_by_class('pci-sriov')

        sriov_configs = []
        for interface in sriov_interfaces:
            # get all data networks
            data_networks = SystemInterfaceDatanetworkKeywords(self.ssh_connection).interface_datanetwork_list(hostname)

            # get datanetwork with the specified interface name
            data_network = data_networks.get_system_interface_datanetwork_by_interface_name(interface.get_name())

            # get host interface
            host_interface = SystemHostInterfaceKeywords(self.ssh_connection).system_host_interface_show(hostname, interface.get_name())

            sriov_configs.append(SriovConfigObject(host_interface, data_network))

        return sriov_configs
