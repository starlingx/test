"""Project object representing a Keystone project."""


class ProjectObject:
    """Represents a single Keystone project."""

    def __init__(self) -> None:
        """Initialize ProjectObject with empty values."""
        self.id: str = ""
        self.name: str = ""
        self.domain_id: str = ""
        self.description: str = ""

    def get_id(self) -> str:
        """Get project ID.

        Returns:
            str: Project UUID.
        """
        return self.id

    def set_id(self, value: str) -> None:
        """Set project ID.

        Args:
            value (str): Project UUID.
        """
        self.id = value

    def get_name(self) -> str:
        """Get project name.

        Returns:
            str: Project name.
        """
        return self.name

    def set_name(self, value: str) -> None:
        """Set project name.

        Args:
            value (str): Project name.
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

    def get_description(self) -> str:
        """Get project description.

        Returns:
            str: Project description.
        """
        return self.description

    def set_description(self, value: str) -> None:
        """Set project description.

        Args:
            value (str): Project description.
        """
        self.description = value

    def __str__(self) -> str:
        """Human-readable summary.

        Returns:
            str: Summary string.
        """
        return f"ProjectObject(id={self.id}, name={self.name}, domain={self.domain_id})"
