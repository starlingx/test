"""OpenStack port list output parsing."""

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.openstack_table_parser import OpenStackTableParser
from keywords.cloud_platform.openstack.port.object.openstack_port_list_object import OpenStackPortListObject


class OpenStackPortListOutput:
    """Class for openstack port list output.

    Handles continuation lines where a port has multiple Fixed IP Addresses.
    The parser returns each line as a separate dict. Lines with an empty ID
    are continuation lines whose Fixed IP Addresses belong to the previous
    port.
    """

    def __init__(self, openstack_port_list_output):
        """Initialize OpenStackPortListOutput.

        Args:
            openstack_port_list_output: Raw CLI output to parse.
        """
        self.openstack_port_list_objects: list[OpenStackPortListObject] = []
        openstack_table_parser = OpenStackTableParser(openstack_port_list_output)
        output_values = openstack_table_parser.get_output_values_list()

        for value in output_values:
            if value["ID"]:
                port_object = OpenStackPortListObject()
                port_object.set_id(value["ID"])
                port_object.set_name(value["Name"])
                port_object.set_mac_address(value["MAC Address"])
                port_object.set_fixed_ip_addresses(value["Fixed IP Addresses"])
                port_object.set_status(value["Status"])
                self.openstack_port_list_objects.append(port_object)
            elif self.openstack_port_list_objects:
                extra = value["Fixed IP Addresses"]
                if extra:
                    self.openstack_port_list_objects[-1].append_fixed_ip_addresses(extra)

    def get_ports(self) -> list[OpenStackPortListObject]:
        """Get the list of port objects.

        Returns:
            list[OpenStackPortListObject]: List of port objects.
        """
        return self.openstack_port_list_objects

    def get_port_by_id(self, port_id: str) -> OpenStackPortListObject:
        """Get the port with the given id.

        Args:
            port_id (str): Port id.

        Returns:
            OpenStackPortListObject: The port object with the given id.

        Raises:
            KeywordException: If no port is found with the given id.
        """
        for port in self.openstack_port_list_objects:
            if port.get_id() == port_id:
                return port
        raise KeywordException(f"No port was found with id {port_id}")

    def get_port_by_name(self, name: str) -> OpenStackPortListObject:
        """Get the port with the given name.

        Args:
            name (str): Port name.

        Returns:
            OpenStackPortListObject: The port object with the given name.

        Raises:
            KeywordException: If no port is found with the given name.
        """
        for port in self.openstack_port_list_objects:
            if port.get_name() == name:
                return port
        raise KeywordException(f"No port was found with name {name}")

    def get_ports_by_status(self, status: str) -> list[OpenStackPortListObject]:
        """Get all ports with the given status.

        Args:
            status (str): Port status (e.g. ACTIVE, DOWN).

        Returns:
            list[OpenStackPortListObject]: List of matching port objects.
        """
        return [p for p in self.openstack_port_list_objects if p.get_status() == status]

    def is_port(self, port_id: str) -> bool:
        """Check if a port with the given id exists.

        Args:
            port_id (str): Port id.

        Returns:
            bool: True if the port exists, False otherwise.
        """
        for port in self.openstack_port_list_objects:
            if port.get_id() == port_id:
                return True
        return False
