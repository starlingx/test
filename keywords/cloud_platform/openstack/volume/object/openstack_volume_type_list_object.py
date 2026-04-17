"""OpenStack volume type list data object."""


class OpenStackVolumeTypeListObject:
    """Object to represent a single row of the 'openstack volume type list' command."""

    def __init__(self):
        """Initialize OpenStackVolumeTypeListObject."""
        self.id = None
        self.name = None
        self.is_public = None

    def set_id(self, id: str):
        """Set the volume type id.

        Args:
            id (str): Volume type id.
        """
        self.id = id

    def get_id(self) -> str:
        """Get the volume type id.

        Returns:
            str: Volume type id.
        """
        return self.id

    def set_name(self, name: str):
        """Set the volume type name.

        Args:
            name (str): Volume type name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get the volume type name.

        Returns:
            str: Volume type name.
        """
        return self.name

    def set_is_public(self, is_public: str):
        """Set whether the volume type is public.

        Args:
            is_public (str): 'True' or 'False' string from CLI output.
        """
        self.is_public = is_public

    def get_is_public(self) -> str:
        """Get whether the volume type is public.

        Returns:
            str: 'True' or 'False' string.
        """
        return self.is_public

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Human-readable volume type summary.
        """
        return f"VolumeType(id={self.id}, name={self.name}, is_public={self.is_public})"
