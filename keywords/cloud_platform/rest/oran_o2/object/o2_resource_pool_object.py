class O2ResourcePoolObject:
    """Represents a single O2 IMS resource pool.

    Models only the field the tests assert (`resourcePoolId`).
    """

    def __init__(self, resource_pool_id: str):
        """Constructor.

        Args:
            resource_pool_id (str): The resourcePoolId value.
        """
        self.resource_pool_id = resource_pool_id

    def get_resource_pool_id(self) -> str:
        """Get the resource pool id.

        Returns:
            str: The resourcePoolId value.
        """
        return self.resource_pool_id
