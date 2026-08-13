"""Object class for host sensor group."""


class HostSensorgroupObject:
    """Represents a host sensor group."""

    def __init__(self):
        """Initialize HostSensorgroupObject."""
        self.uuid: str = None
        self.sensorgroupname: str = None
        self.status: str = None

    def set_uuid(self, uuid: str):
        """Set the UUID.

        Args:
            uuid (str): The sensorgroup UUID.
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """Get the UUID.

        Returns:
            str: The sensorgroup UUID.
        """
        return self.uuid

    def set_sensorgroupname(self, sensorgroupname: str):
        """Set the sensor group name.

        Args:
            sensorgroupname (str): The sensor group name.
        """
        self.sensorgroupname = sensorgroupname

    def get_sensorgroupname(self) -> str:
        """Get the sensor group name.

        Returns:
            str: The sensor group name.
        """
        return self.sensorgroupname

    def set_status(self, status: str):
        """Set the status.

        Args:
            status (str): The sensorgroup status.
        """
        self.status = status

    def get_status(self) -> str:
        """Get the status.

        Returns:
            str: The sensorgroup status.
        """
        return self.status
