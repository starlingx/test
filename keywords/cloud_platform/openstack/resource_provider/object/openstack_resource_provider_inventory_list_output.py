"""OpenStack resource provider inventory list output parsing."""

from typing import List

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.resource_provider.object.openstack_resource_provider_inventory_list_object import OpenStackResourceProviderInventoryListObject


class OpenStackResourceProviderInventoryListOutput:
    """Class for openstack resource provider inventory list output via OpenStack SDK."""

    def __init__(self, inventories_response: dict, usages: dict):
        """Initialize from Placement API inventory and usage responses.

        The Placement API returns inventories as::

            {
                "inventories": {
                    "VCPU": {"total": 128, "reserved": 0, "allocation_ratio": 16.0, ...},
                    "MEMORY_MB": {...},
                    "DISK_GB": {...},
                },
                "resource_provider_generation": 7
            }

        And usages as::

            {
                "VCPU": 54,
                "MEMORY_MB": 110592,
                "DISK_GB": 100,
            }

        Args:
            inventories_response (dict): JSON response from /resource_providers/{uuid}/inventories.
            usages (dict): Mapping of resource_class to used count from /resource_providers/{uuid}/usages.
        """
        self.openstack_resource_provider_inventory_list_objects: List[OpenStackResourceProviderInventoryListObject] = []
        inventories = inventories_response.get("inventories", {})

        for resource_class, inv_data in inventories.items():
            resource_provider_object = OpenStackResourceProviderInventoryListObject()
            resource_provider_object.set_resource_class(resource_class)
            resource_provider_object.set_allocation_ratio(float(inv_data.get("allocation_ratio", 1.0)))
            resource_provider_object.set_min_unit(int(inv_data.get("min_unit", 1)))
            resource_provider_object.set_max_unit(int(inv_data.get("max_unit", 0)))
            resource_provider_object.set_reserved(int(inv_data.get("reserved", 0)))
            resource_provider_object.set_step_size(int(inv_data.get("step_size", 1)))
            resource_provider_object.set_total(int(inv_data.get("total", 0)))
            resource_provider_object.set_used(int(usages.get(resource_class, 0)))

            self.openstack_resource_provider_inventory_list_objects.append(resource_provider_object)

    def get_resource_providers(self) -> List[OpenStackResourceProviderInventoryListObject]:
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
