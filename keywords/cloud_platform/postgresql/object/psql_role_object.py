class PsqlRoleObject:
    """Represents a single role from psql \\du output."""

    def __init__(self) -> None:
        """Initialize PsqlRoleObject."""
        self.name: str = ""
        self.attributes: str = ""

    def set_name(self, name: str) -> None:
        """Set the role name.

        Args:
            name (str): Role name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get the role name.

        Returns:
            str: Role name.
        """
        return self.name

    def set_attributes(self, attributes: str) -> None:
        """Set the role attributes.

        Args:
            attributes (str): Attributes string.
        """
        self.attributes = attributes

    def get_attributes(self) -> str:
        """Get the role attributes.

        Returns:
            str: Attributes string.
        """
        return self.attributes

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: String representation.
        """
        return f"{self.name} ({self.attributes})"
