from keywords.cloud_platform.rest.oran_o2.object.o2_resource_pool_object import O2ResourcePoolObject
from keywords.cloud_platform.rest.oran_o2.object.o2_rest_response import O2RestResponse


class O2ResourcePoolsOutput:
    """Parses the O2 IMS resourcePools list response into resource pool objects."""

    def __init__(self, response: O2RestResponse):
        """Initialize from an O2 REST response.

        Accepts both shapes the endpoint returns: the list read yields an array of
        entries, while a detail read yields a single entry, which is normalized to
        a one-element list so both are read the same way.

        Args:
            response (O2RestResponse): The response from a resourcePools list or
                detail endpoint.
        """
        self.resource_pools = []
        content = response.get_json_content() or []
        if isinstance(content, dict):
            content = [content]
        for entry in content:
            resource_pool_id = entry.get("resourcePoolId", "")
            if resource_pool_id:
                self.resource_pools.append(O2ResourcePoolObject(resource_pool_id))

    def get_resource_pools(self) -> list[O2ResourcePoolObject]:
        """Get all resource pool objects.

        Returns:
            list[O2ResourcePoolObject]: The parsed resource pools.
        """
        return self.resource_pools

    def is_empty(self) -> bool:
        """Return whether the resource pool list is empty.

        Returns:
            bool: True if no resource pools were parsed.
        """
        return len(self.resource_pools) == 0

    def get_first(self) -> O2ResourcePoolObject:
        """Get the first resource pool.

        Returns:
            O2ResourcePoolObject: The first resource pool.

        Raises:
            ValueError: If the resource pool list is empty.
        """
        if not self.resource_pools:
            raise ValueError("No resource pools were returned")
        return self.resource_pools[0]
