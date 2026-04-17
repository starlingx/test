"""OpenStack volume list data object."""


class OpenStackVolumeListObject:
    """Object to represent a single row of the 'openstack volume list' command."""

    def __init__(self):
        """Initialize OpenStackVolumeListObject."""
        self.id = None
        self.name = None
        self.status = None
        self.size = None
        self.attached_to = None

    def set_id(self, id: str):
        """Set the volume id.

        Args:
            id (str): Volume id.
        """
        self.id = id

    def get_id(self) -> str:
        """Get the volume id.

        Returns:
            str: Volume id.
        """
        return self.id

    def set_name(self, name: str):
        """Set the volume name.

        Args:
            name (str): Volume name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get the volume name.

        Returns:
            str: Volume name.
        """
        return self.name

    def set_status(self, status: str):
        """Set the volume status.

        Args:
            status (str): Volume status (e.g. 'available', 'in-use', 'error').
        """
        self.status = status

    def get_status(self) -> str:
        """Get the volume status.

        Returns:
            str: Volume status (e.g. 'available', 'in-use', 'error').
        """
        return self.status

    def set_size(self, size: str):
        """Set the volume size in GB.

        Args:
            size (str): Volume size in GB as string from CLI output.
        """
        self.size = size

    def get_size(self) -> str:
        """Get the volume size in GB.

        Returns:
            str: Volume size in GB as string.
        """
        return self.size

    def get_size_as_int(self) -> int:
        """Get the volume size as an integer.

        Returns:
            int: Volume size in GB.
        """
        return int(self.size)

    def set_attached_to(self, attached_to: str):
        """Set the server attachment info.

        Args:
            attached_to (str): Server attachment string from CLI output.
        """
        self.attached_to = attached_to

    def get_attached_to(self) -> str:
        """Get the server attachment info.

        Returns:
            str: Server attachment string.
        """
        return self.attached_to

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Human-readable volume summary.
        """
        return f"Volume(id={self.id}, name={self.name}, " f"status={self.status}, size={self.size}GB, " f"attached_to={self.attached_to})"
