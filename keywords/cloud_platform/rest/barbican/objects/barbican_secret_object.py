"""Object class for Barbican Secret."""


class BarbicanSecretObject:
    """Represents a Barbican secret resource."""

    def __init__(self):
        """Initialize BarbicanSecretObject."""
        self.secret_ref: str = None
        self.name: str = None
        self.status: str = None
        self.created: str = None

    def set_secret_ref(self, secret_ref: str):
        """Set the secret ref.

        Args:
            secret_ref (str): The secret reference URL.
        """
        self.secret_ref = secret_ref

    def get_secret_ref(self) -> str:
        """Get the secret ref.

        Returns:
            str: The secret reference URL.
        """
        return self.secret_ref

    def get_secret_id(self) -> str:
        """Get the secret UUID derived from the secret_ref.

        Returns:
            str: The secret UUID, or None if secret_ref is not set.
        """
        if self.secret_ref is None:
            return None
        parts = self.secret_ref.split("/v1/secrets/")
        if len(parts) == 2:
            return parts[1]
        return None

    def set_name(self, name: str):
        """Set the secret name.

        Args:
            name (str): The secret name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get the secret name.

        Returns:
            str: The secret name.
        """
        return self.name

    def set_status(self, status: str):
        """Set the secret status.

        Args:
            status (str): The secret status.
        """
        self.status = status

    def get_status(self) -> str:
        """Get the secret status.

        Returns:
            str: The secret status.
        """
        return self.status

    def set_created(self, created: str):
        """Set the created timestamp.

        Args:
            created (str): The created timestamp.
        """
        self.created = created

    def get_created(self) -> str:
        """Get the created timestamp.

        Returns:
            str: The created timestamp.
        """
        return self.created
