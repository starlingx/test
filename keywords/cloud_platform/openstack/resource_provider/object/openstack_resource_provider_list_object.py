"""OpenStack resource provider list data object."""


class OpenStackResourceProviderListObject:
    """Object to represent a row from the 'openstack resource provider list' command."""

    def __init__(self):
        """Initialize OpenStackResourceProviderListObject."""
        self.uuid = None
        self.name = None
        self.generation = None
        self.root_provider_uuid = None
        self.parent_provider_uuid = None

    def set_uuid(self, uuid: str):
        """Set the resource provider UUID.

        Args:
            uuid (str): Resource provider UUID.
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """Get the resource provider UUID.

        Returns:
            str: Resource provider UUID.
        """
        return self.uuid

    def set_name(self, name: str):
        """Set the resource provider name.

        Args:
            name (str): Resource provider name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get the resource provider name.

        Returns:
            str: Resource provider name.
        """
        return self.name

    def set_generation(self, generation: int):
        """Set the resource provider generation.

        Args:
            generation (int): Resource provider generation.
        """
        self.generation = generation

    def get_generation(self) -> int:
        """Get the resource provider generation.

        Returns:
            int: Resource provider generation.
        """
        return self.generation

    def set_root_provider_uuid(self, root_provider_uuid: str):
        """Set the root provider UUID.

        Args:
            root_provider_uuid (str): Root provider UUID.
        """
        self.root_provider_uuid = root_provider_uuid

    def get_root_provider_uuid(self) -> str:
        """Get the root provider UUID.

        Returns:
            str: Root provider UUID.
        """
        return self.root_provider_uuid

    def set_parent_provider_uuid(self, parent_provider_uuid: str):
        """Set the parent provider UUID.

        Args:
            parent_provider_uuid (str): Parent provider UUID.
        """
        self.parent_provider_uuid = parent_provider_uuid

    def get_parent_provider_uuid(self) -> str:
        """Get the parent provider UUID.

        Returns:
            str: Parent provider UUID.
        """
        return self.parent_provider_uuid

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Human-readable resource provider summary.
        """
        return f"OpenStackResourceProviderListObject(" f"uuid={self.uuid}, name={self.name}, " f"generation={self.generation}, " f"root_provider_uuid={self.root_provider_uuid}, " f"parent_provider_uuid={self.parent_provider_uuid})"
