class O2ResourceTypeObject:
    """Represents a single O2 IMS resource type.

    Models only the field the tests assert (`resourceTypeId`); other fields such
    as `alarmDictionary` are intentionally not modelled.
    """

    def __init__(self, resource_type_id: str):
        """Constructor.

        Args:
            resource_type_id (str): The resourceTypeId value.
        """
        self.resource_type_id = resource_type_id

    def get_resource_type_id(self) -> str:
        """Get the resource type id.

        Returns:
            str: The resourceTypeId value.
        """
        return self.resource_type_id
