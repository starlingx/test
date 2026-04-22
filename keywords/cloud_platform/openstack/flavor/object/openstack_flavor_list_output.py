"""OpenStack flavor list output parsing."""

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.flavor.object.openstack_flavor_list_object import OpenStackFlavorListObject
from keywords.cloud_platform.openstack.openstack_table_parser import OpenStackTableParser


class OpenStackFlavorListOutput:
    """Class for openstack flavor list output."""

    def __init__(self, openstack_flavor_list_output):
        """Initialize OpenStackFlavorListOutput.

        Args:
            openstack_flavor_list_output: Raw CLI output to parse.
        """
        self.openstack_flavor_list_objects: list[OpenStackFlavorListObject] = []
        openstack_table_parser = OpenStackTableParser(openstack_flavor_list_output)
        output_values = openstack_table_parser.get_output_values_list()

        for value in output_values:
            flavor_object = OpenStackFlavorListObject()
            flavor_object.set_id(value["ID"])
            flavor_object.set_name(value["Name"])
            flavor_object.set_ram(value["RAM"])
            flavor_object.set_disk(value["Disk"])
            flavor_object.set_ephemeral(value["Ephemeral"])
            flavor_object.set_vcpus(value["VCPUs"])
            flavor_object.set_is_public(value["Is Public"])

            self.openstack_flavor_list_objects.append(flavor_object)

    def get_flavors(self) -> list[OpenStackFlavorListObject]:
        """Get the list of flavor objects.

        Returns:
            list[OpenStackFlavorListObject]: List of flavor objects.
        """
        return self.openstack_flavor_list_objects

    def get_flavor_by_name(self, name: str) -> OpenStackFlavorListObject:
        """Get the flavor with the given name.

        Args:
            name (str): Flavor name.

        Returns:
            OpenStackFlavorListObject: The flavor object with the given name.

        Raises:
            KeywordException: If no flavor is found with the given name.
        """
        for flavor in self.openstack_flavor_list_objects:
            if flavor.get_name() == name:
                return flavor
        raise KeywordException(f"No flavor was found with name {name}")

    def get_flavor_by_id(self, flavor_id: str) -> OpenStackFlavorListObject:
        """Get the flavor with the given id.

        Args:
            flavor_id (str): Flavor id.

        Returns:
            OpenStackFlavorListObject: The flavor object with the given id.

        Raises:
            KeywordException: If no flavor is found with the given id.
        """
        for flavor in self.openstack_flavor_list_objects:
            if flavor.get_id() == flavor_id:
                return flavor
        raise KeywordException(f"No flavor was found with id {flavor_id}")

    def is_flavor(self, name: str) -> bool:
        """Check if a flavor with the given name exists.

        Args:
            name (str): Flavor name.

        Returns:
            bool: True if the flavor exists, False otherwise.
        """
        for flavor in self.openstack_flavor_list_objects:
            if flavor.get_name() == name:
                return True
        return False
