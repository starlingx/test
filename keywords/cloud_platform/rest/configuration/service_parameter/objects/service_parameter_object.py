"""Object class for ServiceParameterObject."""


class ServiceParameterObject:
    """Represents a ServiceParameterObject resource."""

    def __init__(self):
        """Initialize ServiceParameterObject."""
        self.uuid: str = None
        self.service: str = None
        self.section: str = None
        self.name: str = None
        self.value: str = None

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

    def set_service(self, service: str):
        """Set service.

        Args:
            service (str): The service.
        """
        self.service = service

    def get_service(self) -> str:
        """Get service.

        Returns:
            str: The service.
        """
        return self.service

    def set_section(self, section: str):
        """Set section.

        Args:
            section (str): The section.
        """
        self.section = section

    def get_section(self) -> str:
        """Get section.

        Returns:
            str: The section.
        """
        return self.section

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

    def set_value(self, value: str):
        """Set value.

        Args:
            value (str): The value.
        """
        self.value = value

    def get_value(self) -> str:
        """Get value.

        Returns:
            str: The value.
        """
        return self.value

