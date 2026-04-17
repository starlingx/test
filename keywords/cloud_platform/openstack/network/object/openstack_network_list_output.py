"""OpenStack network list output parsing."""

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.network.object.openstack_network_list_object import OpenStackNetworkListObject
from keywords.cloud_platform.openstack.openstack_table_parser import OpenStackTableParser


class OpenStackNetworkListOutput:
    """Class for openstack network list output."""

    def __init__(self, openstack_network_list_output):
        """Initialize OpenStackNetworkListOutput.

        Args:
            openstack_network_list_output: Raw CLI output to parse.
        """
        self.openstack_network_list_objects: list[OpenStackNetworkListObject] = []
        openstack_table_parser = OpenStackTableParser(openstack_network_list_output)
        output_values = openstack_table_parser.get_output_values_list()

        for value in output_values:
            network_object = OpenStackNetworkListObject()
            network_object.set_id(value["ID"])
            network_object.set_name(value["Name"])
            network_object.set_subnets(value["Subnets"])

            self.openstack_network_list_objects.append(network_object)

    def get_networks(self) -> list[OpenStackNetworkListObject]:
        """Get the list of network objects.

        Returns:
            list[OpenStackNetworkListObject]: List of network objects.
        """
        return self.openstack_network_list_objects

    def get_network_by_name(self, name: str) -> OpenStackNetworkListObject:
        """Get the network with the given name.

        Args:
            name (str): Network name.

        Returns:
            OpenStackNetworkListObject: The network object with the given name.

        Raises:
            KeywordException: If no network is found with the given name.
        """
        for network in self.openstack_network_list_objects:
            if network.get_name() == name:
                return network
        raise KeywordException(f"No network was found with name {name}")

    def get_network_by_id(self, network_id: str) -> OpenStackNetworkListObject:
        """Get the network with the given id.

        Args:
            network_id (str): Network id.

        Returns:
            OpenStackNetworkListObject: The network object with the given id.

        Raises:
            KeywordException: If no network is found with the given id.
        """
        for network in self.openstack_network_list_objects:
            if network.get_id() == network_id:
                return network
        raise KeywordException(f"No network was found with id {network_id}")

    def is_network(self, name: str) -> bool:
        """Check if a network with the given name exists.

        Args:
            name (str): Network name.

        Returns:
            bool: True if the network exists, False otherwise.
        """
        for network in self.openstack_network_list_objects:
            if network.get_name() == name:
                return True
        return False
