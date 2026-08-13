"""Object class for LLDP."""


class LldpObject:
    """Represents an LLDP agent or neighbour."""

    def __init__(self):
        """Initialize LldpObject."""
        self.uuid: str = None
        self.port_identifier: str = None
        self.chassis_id: str = None

    def set_uuid(self, uuid: str):
        """Set UUID.

        Args:
            uuid (str): The UUID.
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """Get UUID.

        Returns:
            str: The UUID.
        """
        return self.uuid

    def set_port_identifier(self, port_identifier: str):
        """Set port identifier.

        Args:
            port_identifier (str): The port identifier.
        """
        self.port_identifier = port_identifier

    def get_port_identifier(self) -> str:
        """Get port identifier.

        Returns:
            str: The port identifier.
        """
        return self.port_identifier

    def set_chassis_id(self, chassis_id: str):
        """Set chassis ID.

        Args:
            chassis_id (str): The chassis ID.
        """
        self.chassis_id = chassis_id

    def get_chassis_id(self) -> str:
        """Get chassis ID.

        Returns:
            str: The chassis ID.
        """
        return self.chassis_id
