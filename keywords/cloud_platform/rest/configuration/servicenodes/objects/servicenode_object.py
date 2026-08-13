"""Object class for ServicenodeObject."""


class ServicenodeObject:
    """Represents a ServicenodeObject resource."""

    def __init__(self):
        """Initialize ServicenodeObject."""
        self.uuid: str = None
        self.name: str = None
        self.operational_state: str = None

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

    def set_operational_state(self, operational_state: str):
        """Set operational_state.

        Args:
            operational_state (str): The operational_state.
        """
        self.operational_state = operational_state

    def get_operational_state(self) -> str:
        """Get operational_state.

        Returns:
            str: The operational_state.
        """
        return self.operational_state

