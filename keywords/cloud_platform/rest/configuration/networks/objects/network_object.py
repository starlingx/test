"""Object class for NetworkObject."""


class NetworkObject:
    """Represents a NetworkObject resource."""

    def __init__(self):
        """Initialize NetworkObject."""
        self.uuid: str = None
        self.name: str = None
        self.type: str = None

    def set_uuid(self, uuid: str):
        """Set uuid.

        Args:
            uuid (str): The uuid.
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """Get uuid.

        Returns:
            str: The uuid.
        """
        return self.uuid

    def set_name(self, name: str):
        """Set name.

        Args:
            name (str): The name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get name.

        Returns:
            str: The name.
        """
        return self.name

    def set_type(self, type: str):
        """Set type.

        Args:
            type (str): The type.
        """
        self.type = type

    def get_type(self) -> str:
        """Get type.

        Returns:
            str: The type.
        """
        return self.type

