class PsqlDatabaseObject:
    """Represents a single database from psql -l output."""

    def __init__(self) -> None:
        """Initialize PsqlDatabaseObject."""
        self.name: str = ""
        self.owner: str = ""
        self.encoding: str = ""

    def set_name(self, name: str) -> None:
        """Set the database name.

        Args:
            name (str): Database name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get the database name.

        Returns:
            str: Database name.
        """
        return self.name

    def set_owner(self, owner: str) -> None:
        """Set the database owner.

        Args:
            owner (str): Owner name.
        """
        self.owner = owner

    def get_owner(self) -> str:
        """Get the database owner.

        Returns:
            str: Owner name.
        """
        return self.owner

    def set_encoding(self, encoding: str) -> None:
        """Set the database encoding.

        Args:
            encoding (str): Encoding string.
        """
        self.encoding = encoding

    def get_encoding(self) -> str:
        """Get the database encoding.

        Returns:
            str: Encoding string.
        """
        return self.encoding

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: String representation.
        """
        return f"{self.name} (owner={self.owner}, encoding={self.encoding})"
