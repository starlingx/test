"""Object class for ServiceObject."""


class ServiceObject:
    """Represents a ServiceObject resource."""

    def __init__(self):
        """Initialize ServiceObject."""
        self.uuid: str = None
        self.servicename: str = None
        self.state: str = None

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

    def set_servicename(self, servicename: str):
        """Set servicename.

        Args:
            servicename (str): The servicename.
        """
        self.servicename = servicename

    def get_servicename(self) -> str:
        """Get servicename.

        Returns:
            str: The servicename.
        """
        return self.servicename

    def set_state(self, state: str):
        """Set state.

        Args:
            state (str): The state.
        """
        self.state = state

    def get_state(self) -> str:
        """Get state.

        Returns:
            str: The state.
        """
        return self.state

