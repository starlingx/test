"""Object class for ServicegroupObject."""


class ServicegroupObject:
    """Represents a ServicegroupObject resource."""

    def __init__(self):
        """Initialize ServicegroupObject."""
        self.uuid: str = None
        self.service_group_name: str = None
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

    def set_service_group_name(self, service_group_name: str):
        """Set service_group_name.

        Args:
            service_group_name (str): The service_group_name.
        """
        self.service_group_name = service_group_name

    def get_service_group_name(self) -> str:
        """Get service_group_name.

        Returns:
            str: The service_group_name.
        """
        return self.service_group_name

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

