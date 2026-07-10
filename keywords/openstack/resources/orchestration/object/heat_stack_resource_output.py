"""Output parser for Heat stack resource SDK responses."""

from typing import List

from keywords.openstack.resources.orchestration.object.heat_stack_resource_object import HeatStackResourceObject


class HeatStackResourceOutput:
    """Parses OpenStack SDK stack resource dicts into HeatStackResourceObject instances."""

    def __init__(self, raw_resources: List[dict]):
        """Initialize and parse resource dicts.

        Args:
            raw_resources (List[dict]): List of resource dicts from SDK to_dict().
        """
        self.resources: List[HeatStackResourceObject] = []
        for raw in raw_resources:
            resource = HeatStackResourceObject()
            resource.set_resource_name(raw.get("resource_name", ""))
            resource.set_resource_type(raw.get("resource_type", ""))
            resource.set_resource_status(raw.get("resource_status", ""))
            resource.set_resource_status_reason(raw.get("resource_status_reason"))
            resource.set_physical_resource_id(raw.get("physical_resource_id"))
            resource.set_logical_resource_id(raw.get("logical_resource_id"))
            resource.set_updated_time(raw.get("updated_time"))
            self.resources.append(resource)

    def get_resources(self) -> List[HeatStackResourceObject]:
        """Get the list of parsed resources.

        Returns:
            List[HeatStackResourceObject]: List of resource objects.
        """
        return self.resources

    def get_resource_by_type(self, resource_type: str) -> HeatStackResourceObject:
        """Get the first resource matching a type.

        Args:
            resource_type (str): OpenStack resource type (e.g. 'OS::Cinder::Volume').

        Returns:
            HeatStackResourceObject: Matching resource.

        Raises:
            ValueError: If no resource with that type is found.
        """
        for resource in self.resources:
            if resource.get_resource_type() == resource_type:
                return resource
        raise ValueError(f"Resource of type '{resource_type}' not found")

    def get_resource_by_name(self, resource_name: str) -> HeatStackResourceObject:
        """Get a resource by logical name.

        Args:
            resource_name (str): Logical resource name from the template.

        Returns:
            HeatStackResourceObject: Matching resource.

        Raises:
            ValueError: If no resource with that name is found.
        """
        for resource in self.resources:
            if resource.get_resource_name() == resource_name:
                return resource
        raise ValueError(f"Resource '{resource_name}' not found")

    def has_resource_type(self, resource_type: str, resource_name: str = None) -> bool:
        """Check if a resource type exists in the output.

        Args:
            resource_type (str): OpenStack resource type (e.g. 'OS::Cinder::Volume').
            resource_name (str): Optional logical resource name to match.

        Returns:
            bool: True if resource exists.
        """
        for resource in self.resources:
            if resource.get_resource_type() == resource_type:
                if resource_name is None or resource.get_resource_name() == resource_name:
                    return True
        return False

    def is_empty(self) -> bool:
        """Check if the output contains no resources.

        Returns:
            bool: True if no resources in output.
        """
        return len(self.resources) == 0
