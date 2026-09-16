from keywords.cloud_platform.rest.oran_o2.object.o2_resource_type_object import O2ResourceTypeObject
from keywords.cloud_platform.rest.oran_o2.object.o2_rest_response import O2RestResponse


class O2ResourceTypesOutput:
    """Parses the O2 IMS resourceTypes list response into resource type objects."""

    def __init__(self, response: O2RestResponse):
        """Initialize from an O2 REST response.

        Accepts both shapes the endpoint returns: the list read yields an array of
        entries, while a detail read yields a single entry, which is normalized to
        a one-element list so both are read the same way.

        Args:
            response (O2RestResponse): The response from a resourceTypes list or
                detail endpoint.
        """
        self.resource_types = []
        content = response.get_json_content() or []
        if isinstance(content, dict):
            content = [content]
        for entry in content:
            resource_type_id = entry.get("resourceTypeId", "")
            if resource_type_id:
                self.resource_types.append(O2ResourceTypeObject(resource_type_id))

    def get_resource_types(self) -> list[O2ResourceTypeObject]:
        """Get all resource type objects.

        Returns:
            list[O2ResourceTypeObject]: The parsed resource types.
        """
        return self.resource_types

    def is_empty(self) -> bool:
        """Return whether the resource type list is empty.

        Returns:
            bool: True if no resource types were parsed.
        """
        return len(self.resource_types) == 0

    def get_first(self) -> O2ResourceTypeObject:
        """Get the first resource type.

        Returns:
            O2ResourceTypeObject: The first resource type.

        Raises:
            ValueError: If the resource type list is empty.
        """
        if not self.resource_types:
            raise ValueError("No resource types were returned")
        return self.resource_types[0]
