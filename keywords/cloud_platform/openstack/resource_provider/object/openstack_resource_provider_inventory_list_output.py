"""OpenStack resource provider inventory list output parsing."""

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.resource_provider.object.openstack_resource_provider_inventory_list_object import OpenStackResourceProviderInventoryListObject
from keywords.cloud_platform.openstack.openstack_table_parser import OpenStackTableParser


class OpenStackResourceProviderInventoryListOutput:
    """Class for openstack resource provider inventory list output."""

    def __init__(self, openstack_resource_provider_inventory_list_output):
        """Initialize OpenStackResourceProviderInventoryListOutput.

        Args:
            openstack_resource_provider_inventory_list_output: Raw CLI output.
        """
        self.openstack_resource_provider_inventory_list_objects: [OpenStackResourceProviderInventoryListObject] = []
        openstack_table_parser = OpenStackTableParser(openstack_resource_provider_inventory_list_output)
        output_values = openstack_table_parser.get_output_values_list()

        for value in output_values:
            resource_provider_object = OpenStackResourceProviderInventoryListObject()
            resource_provider_object.set_resource_class(value["resource_class"])
            resource_provider_object.set_allocation_ratio(float(value["allocation_ratio"]))
            resource_provider_object.set_min_unit(int(value["min_unit"]))
            resource_provider_object.set_max_unit(int(value["max_unit"]))
            resource_provider_object.set_reserved(int(value["reserved"]))
            resource_provider_object.set_step_size(int(value["step_size"]))
            resource_provider_object.set_total(int(value["total"]))
            resource_provider_object.set_used(int(value["used"]))

            self.openstack_resource_provider_inventory_list_objects.append(resource_provider_object)

    def get_resource_providers(self) -> [OpenStackResourceProviderInventoryListObject]:
        """Get the list of resource provider inventory objects.

        Returns:
            list[OpenStackResourceProviderInventoryListObject]: List of resource provider inventory objects.
        """
        return self.openstack_resource_provider_inventory_list_objects

    def get_resource_provider_by_resource_class(self, resource_class: str) -> OpenStackResourceProviderInventoryListObject:
        """Get the resource provider inventory with the given resource class.

        Args:
            resource_class (str): Resource class name (e.g. VCPU, MEMORY_MB, DISK_GB).

        Returns:
            OpenStackResourceProviderInventoryListObject: The resource provider inventory object.

        Raises:
            KeywordException: If no inventory entry is found for the given resource class.
        """
        for resource_provider in self.openstack_resource_provider_inventory_list_objects:
            if resource_provider.get_resource_class() == resource_class:
                return resource_provider
        raise KeywordException(f"No resource provider was found with resource class {resource_class}")

    def is_resource_provider(self, resource_class: str) -> bool:
        """Check if a resource provider inventory with the given resource class exists.

        Args:
            resource_class (str): Resource class name (e.g. VCPU, MEMORY_MB, DISK_GB).

        Returns:
            bool: True if the resource provider inventory exists, False otherwise.
        """
        for resource_provider in self.openstack_resource_provider_inventory_list_objects:
            if resource_provider.get_resource_class() == resource_class:
                return True
        return False
