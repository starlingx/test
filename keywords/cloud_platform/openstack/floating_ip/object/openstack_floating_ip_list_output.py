"""OpenStack floating ip list output parsing."""

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.floating_ip.object.openstack_floating_ip_list_object import OpenStackFloatingIpListObject
from keywords.cloud_platform.openstack.openstack_table_parser import OpenStackTableParser


class OpenStackFloatingIpListOutput:
    """Class for openstack floating ip list output."""

    def __init__(self, openstack_floating_ip_list_output):
        """Initialize OpenStackFloatingIpListOutput.

        Args:
            openstack_floating_ip_list_output: Raw CLI output to parse.
        """
        self.openstack_floating_ip_list_objects: list[OpenStackFloatingIpListObject] = []
        openstack_table_parser = OpenStackTableParser(openstack_floating_ip_list_output)
        output_values = openstack_table_parser.get_output_values_list()

        for value in output_values:
            floating_ip_object = OpenStackFloatingIpListObject()
            floating_ip_object.set_id(value["ID"])
            floating_ip_object.set_floating_ip_address(value["Floating IP Address"])
            floating_ip_object.set_fixed_ip_address(value["Fixed IP Address"])
            floating_ip_object.set_port(value["Port"])
            floating_ip_object.set_floating_network(value["Floating Network"])
            floating_ip_object.set_project(value["Project"])

            self.openstack_floating_ip_list_objects.append(floating_ip_object)

    def get_floating_ips(self) -> list[OpenStackFloatingIpListObject]:
        """Get the list of floating ip objects.

        Returns:
            list[OpenStackFloatingIpListObject]: List of floating ip objects.
        """
        return self.openstack_floating_ip_list_objects

    def get_floating_ip_by_ip_address(self, ip_address: str) -> OpenStackFloatingIpListObject:
        """Get the floating ip with the given ip address.

        Args:
            ip_address (str): floating ip address.

        Returns:
            OpenStackFloatingIpListObject: The floating ip object with the given ip address.
        """
        for floating_ip in self.openstack_floating_ip_list_objects:
            if floating_ip.get_floating_ip_address() == ip_address:
                return floating_ip
        raise KeywordException(f"No floating ip was found with ip address {ip_address}")

    def is_floating_ip(self, ip_address: str) -> bool:
        """Check if a floating ip with the given ip address exists.

        Args:
            ip_address (str): floating ip address.

        Returns:
            bool: True if the floating ip exists, False otherwise.
        """
        for floating_ip in self.openstack_floating_ip_list_objects:
            if floating_ip.get_floating_ip_address() == ip_address:
                return True
        return False
