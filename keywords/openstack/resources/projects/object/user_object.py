"""User object representing a Keystone user."""


class UserObject:
    """Represents a single Keystone user."""

    def __init__(self) -> None:
        """Initialize UserObject with empty values."""
        self.id: str = ""
        self.name: str = ""
        self.domain_id: str = ""

    def get_id(self) -> str:
        """Get user ID.

        Returns:
            str: User UUID.
        """
        return self.id

    def set_id(self, value: str) -> None:
        """Set user ID.

        Args:
            value (str): User UUID.
        """
        self.id = value

    def get_name(self) -> str:
        """Get user name.

        Returns:
            str: User name.
        """
        return self.name

    def set_name(self, value: str) -> None:
        """Set user name.

        Args:
            value (str): User name.
        """
        self.name = value

    def get_domain_id(self) -> str:
        """Get domain ID.

        Returns:
            str: Domain ID.
        """
        return self.domain_id

    def set_domain_id(self, value: str) -> None:
        """Set domain ID.

        Args:
            value (str): Domain ID.
        """
        self.domain_id = value

    def __str__(self) -> str:
        """Human-readable summary.

        Returns:
            str: Summary string.
        """
        return f"UserObject(id={self.id}, name={self.name}, domain={self.domain_id})"
