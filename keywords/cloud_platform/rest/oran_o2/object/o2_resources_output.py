from keywords.cloud_platform.rest.oran_o2.object.o2_resource_object import O2ResourceObject
from keywords.cloud_platform.rest.oran_o2.object.o2_rest_response import O2RestResponse


class O2ResourcesOutput:
    """Parses the O2 IMS resources list response into resource objects."""

    def __init__(self, response: O2RestResponse):
        """Initialize from an O2 REST response.

        Accepts both shapes the endpoint returns: the list read yields an array of
        entries, while a detail read yields a single entry, which is normalized to
        a one-element list so both are read the same way.

        Args:
            response (O2RestResponse): The response from a resources list or detail
                endpoint.
        """
        self.resources = []
        content = response.get_json_content() or []
        if isinstance(content, dict):
            content = [content]
        for entry in content:
            resource_id = entry.get("resourceId", "")
            if resource_id:
                self.resources.append(O2ResourceObject(resource_id))

    def get_resources(self) -> list[O2ResourceObject]:
        """Get all resource objects.

        Returns:
            list[O2ResourceObject]: The parsed resources.
        """
        return self.resources

    def is_empty(self) -> bool:
        """Return whether the resource list is empty.

        Returns:
            bool: True if no resources were parsed.
        """
        return len(self.resources) == 0

    def get_first(self) -> O2ResourceObject:
        """Get the first resource.

        Returns:
            O2ResourceObject: The first resource.

        Raises:
            ValueError: If the resource list is empty.
        """
        if not self.resources:
            raise ValueError("No resources were returned")
        return self.resources[0]
