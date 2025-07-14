from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_route_list_output import SystemHostRouteListOutput


class SystemHostRouteKeywords(BaseKeyword):
    """
    Class for system host list keywords.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): ssh for active controller.
        """
        self.ssh_connection = ssh_connection

    def get_system_host_route_list(self, controller: str) -> SystemHostRouteListOutput:
        """
        Gets the system host route list

        Args:
            controller (str): controller hostname.

        Returns:
            SystemHostRouteListOutput: System host route list output.

        """
        output = self.ssh_connection.send(source_openrc(f"system host-route-list {controller}"))
        self.validate_success_return_code(self.ssh_connection)
        system_host_route_list_output = SystemHostRouteListOutput(output)

        return system_host_route_list_output

    def get_system_host_route_list_if_names(self, controller: str) -> list:
        """
        Gets the system host route list interface names

        Args:
            controller (str): controller hostname.

        Returns:
            list: interface name list.

        """
        system_host_route_list_output = self.get_system_host_route_list(controller)
        ifnames = system_host_route_list_output.get_ifnames()

        return ifnames

    def get_system_host_route_list_networks(self, controller: str) -> list:
        """
        Gets the system host route list networks

        Args:
            controller (str): controller hostname.

        Returns:
            list: Networks list.
        """
        system_host_route_list_output = self.get_system_host_route_list(controller)
        networks = system_host_route_list_output.get_networks()

        return networks

    def get_system_host_route_list_prefix(self, controller: str) -> list:
        """
        Gets the system host route list prefixes

        Args:
            controller (str): controller hostname.

        Returns:
            list: Prefix list.

        """
        system_host_route_list_output = self.get_system_host_route_list(controller)
        prefix_list = system_host_route_list_output.get_prefix()

        return prefix_list

    def get_system_host_route_list_gateway(self, controller: str) -> list:
        """
        Gets the system host route list gateways

        Args:
            controller (str): controller hostname.

        Returns:
            list: List of gateways

        """
        system_host_route_list_output = self.get_system_host_route_list(controller)
        gateway_list = system_host_route_list_output.get_gateway()

        return gateway_list

    def get_system_host_route_list_metrics(self, controller: str) -> list:
        """
        Gets the system host route list metrics

        Args:
            controller (str): controller hostname.

        Returns:
            list: Route metrics list.

        """
        system_host_route_list_output = self.get_system_host_route_list(controller)
        metrics = system_host_route_list_output.get_metrics()

        return metrics
