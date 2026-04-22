"""OpenStack subnet list output parsing."""

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.network.object.openstack_subnet_list_object import OpenStackSubnetListObject
from keywords.cloud_platform.openstack.openstack_table_parser import OpenStackTableParser


class OpenStackSubnetListOutput:
    """Class for openstack subnet list output."""

    def __init__(self, openstack_subnet_list_output):
        """Initialize OpenStackSubnetListOutput.

        Args:
            openstack_subnet_list_output: Raw CLI output to parse.
        """
        self.openstack_subnet_list_objects: list[OpenStackSubnetListObject] = []
        openstack_table_parser = OpenStackTableParser(openstack_subnet_list_output)
        output_values = openstack_table_parser.get_output_values_list()

        for value in output_values:
            subnet_object = OpenStackSubnetListObject()
            subnet_object.set_id(value["ID"])
            subnet_object.set_name(value["Name"])
            subnet_object.set_network(value["Network"])
            subnet_object.set_subnet(value["Subnet"])

            self.openstack_subnet_list_objects.append(subnet_object)

    def get_subnets(self) -> list[OpenStackSubnetListObject]:
        """Get the list of subnet objects.

        Returns:
            list[OpenStackSubnetListObject]: List of subnet objects.
        """
        return self.openstack_subnet_list_objects

    def get_subnet_by_name(self, name: str) -> OpenStackSubnetListObject:
        """Get the subnet with the given name.

        Args:
            name (str): Subnet name.

        Returns:
            OpenStackSubnetListObject: The subnet object with the given name.

        Raises:
            KeywordException: If no subnet is found with the given name.
        """
        for subnet in self.openstack_subnet_list_objects:
            if subnet.get_name() == name:
                return subnet
        raise KeywordException(f"No subnet was found with name {name}")

    def get_subnet_by_id(self, subnet_id: str) -> OpenStackSubnetListObject:
        """Get the subnet with the given id.

        Args:
            subnet_id (str): Subnet id.

        Returns:
            OpenStackSubnetListObject: The subnet object with the given id.

        Raises:
            KeywordException: If no subnet is found with the given id.
        """
        for subnet in self.openstack_subnet_list_objects:
            if subnet.get_id() == subnet_id:
                return subnet
        raise KeywordException(f"No subnet was found with id {subnet_id}")

    def get_subnets_by_network(self, network_id: str) -> list[OpenStackSubnetListObject]:
        """Get all subnets belonging to the given network.

        Args:
            network_id (str): Network id.

        Returns:
            list[OpenStackSubnetListObject]: List of subnets for the network.
        """
        return [subnet for subnet in self.openstack_subnet_list_objects if subnet.get_network() == network_id]

    def is_subnet(self, name: str) -> bool:
        """Check if a subnet with the given name exists.

        Args:
            name (str): Subnet name.

        Returns:
            bool: True if the subnet exists, False otherwise.
        """
        for subnet in self.openstack_subnet_list_objects:
            if subnet.get_name() == name:
                return True
        return False
