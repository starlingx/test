class O2ResourceObject:
    """Represents a single O2 IMS resource.

    Models only the field the tests assert (`resourceId`).
    """

    def __init__(self, resource_id: str):
        """Constructor.

        Args:
            resource_id (str): The resourceId value.
        """
        self.resource_id = resource_id

    def get_resource_id(self) -> str:
        """Get the resource id.

        Returns:
            str: The resourceId value.
        """
        return self.resource_id
