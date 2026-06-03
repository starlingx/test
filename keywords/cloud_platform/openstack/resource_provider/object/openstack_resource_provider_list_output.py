"""OpenStack resource provider list output parsing."""

from typing import List

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.resource_provider.object.openstack_resource_provider_list_object import OpenStackResourceProviderListObject


class OpenStackResourceProviderListOutput:
    """Class for openstack resource provider list output via OpenStack SDK."""

    def __init__(self, sdk_providers: list):
        """Initialize OpenStackResourceProviderListOutput from openstacksdk objects.

        Args:
            sdk_providers (list): List of resource provider objects from
                connection.placement.resource_providers().
        """
        self.openstack_resource_provider_list_objects: List[OpenStackResourceProviderListObject] = []

        for provider in sdk_providers:
            resource_provider_object = OpenStackResourceProviderListObject()
            resource_provider_object.set_uuid(provider.get("uuid", provider.get("id", "")))
            resource_provider_object.set_name(provider.get("name", ""))
            resource_provider_object.set_generation(provider.get("generation", 0))
            resource_provider_object.set_root_provider_uuid(provider.get("root_provider_uuid", ""))
            resource_provider_object.set_parent_provider_uuid(provider.get("parent_provider_uuid", ""))

            self.openstack_resource_provider_list_objects.append(resource_provider_object)

    def get_resource_providers(self) -> List[OpenStackResourceProviderListObject]:
        """Get the list of resource provider objects.

        Returns:
            list[OpenStackResourceProviderListObject]: List of resource provider objects.
        """
        return self.openstack_resource_provider_list_objects

    def get_resource_provider_by_name(self, name: str) -> OpenStackResourceProviderListObject:
        """Get the resource provider with the given name.

        Args:
            name (str): Resource provider name (e.g. compute-0).

        Returns:
            OpenStackResourceProviderListObject: The resource provider object.

        Raises:
            KeywordException: If no resource provider is found with the given name.
        """
        for resource_provider in self.openstack_resource_provider_list_objects:
            if resource_provider.get_name() == name:
                return resource_provider
        raise KeywordException(f"No resource provider was found with name {name}")

    def get_resource_provider_by_uuid(self, uuid: str) -> OpenStackResourceProviderListObject:
        """Get the resource provider with the given UUID.

        Args:
            uuid (str): Resource provider UUID.

        Returns:
            OpenStackResourceProviderListObject: The resource provider object.

        Raises:
            KeywordException: If no resource provider is found with the given UUID.
        """
        for resource_provider in self.openstack_resource_provider_list_objects:
            if resource_provider.get_uuid() == uuid:
                return resource_provider
        raise KeywordException(f"No resource provider was found with uuid {uuid}")

    def is_resource_provider(self, name: str) -> bool:
        """Check if a resource provider with the given name exists.

        Args:
            name (str): Resource provider name.

        Returns:
            bool: True if the resource provider exists, False otherwise.
        """
        for resource_provider in self.openstack_resource_provider_list_objects:
            if resource_provider.get_name() == name:
                return True
        return False
