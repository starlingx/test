from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.host.objects.system_host_route_list_object import SystemHostRouteListObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostRouteListOutput:
    """
    Class for System Host Route List Output
    """

    def __init__(self, system_host_route_list_output):
        self.system_host_route_list: [SystemHostRouteListObject] = []
        system_table_parser = SystemTableParser(system_host_route_list_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                system_host_route_object = SystemHostRouteListObject(value["uuid"], value["ifname"], value["network"], value["prefix"], value["gateway"], value["metric"])
                self.system_host_route_list.append(system_host_route_object)

            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_ifnames(self) -> list:
        """
        Returns the list of system host interfaces

        Returns:
            list: list of system host interfaces
        """
        ifnames_list = [x.get_ifname() for x in self.system_host_route_list]
        return ifnames_list

    def get_networks(self) -> list:
        """
        Returns the list of system networks

        Returns:
            list: list of system networks
        """
        networks_list = [x.get_network() for x in self.system_host_route_list]
        return networks_list

    def get_prefix(self) -> list:
        """
        Returns the list of system networks

        Returns:
            list: list of system networks
        """
        prefix_list = [x.get_prefix() for x in self.system_host_route_list]
        return prefix_list

    def get_gateway(self) -> list:
        """
        Returns the list of system networks

        Returns:
            list: list of system networks
        """
        gateway_list = [x.get_gateway() for x in self.system_host_route_list]
        return gateway_list

    def get_gateway_address(self) -> str:
        """
        Returns the gateway address

        Returns:
            str: A string containing gateway addresses
        """
        return " ".join(self.get_gateway())

    def get_metrics(self) -> list:
        """
        Returns the list of system networks

        Returns:
            list: list of system networks
        """
        metrics_list = [x.get_metric() for x in self.system_host_route_list]
        return metrics_list

    def get_gateway_by_network(self, network: str) -> str:
        """
        Returns the gateway corresponding to a given network from the system host route list.

        Args:
            network (str): Network/subnet string to search for (must match exactly as in system host-route-list).

        Returns:
            str: Gateway IP corresponding to the given network.

        Raises:
            KeywordException: If the network is not found in the system host route list.
        """
        for host_route in self.system_host_route_list:
            if host_route.get_network() == network:
                return host_route.get_gateway()
        raise KeywordException(f"Gateway not found for network '{network}'")

    @staticmethod
    def is_valid_output(value: str) -> bool:
        """
        Checks to ensure the output has the correct keys

        Args:
            value (str): the value to check

        Returns:
            bool: if received values are valid.

        """
        valid = True
        if "uuid" not in value:
            get_logger().log_error(f"uuid is not in the output value: {value}")
            valid = False
        if "ifname" not in value:
            get_logger().log_error(f"ifname is not in the output value: {value}")
            valid = False
        if "network" not in value:
            get_logger().log_error(f"network is not in the output value: {value}")
            valid = False
        if "prefix" not in value:
            get_logger().log_error(f"prefix is not in the output value: {value}")
            valid = False
        if "gateway" not in value:
            get_logger().log_error(f"gateway is not in the output value: {value}")
            valid = False
        if "metric" not in value:
            get_logger().log_error(f"metric is not in the output value: {value}")
            valid = False

        return valid
