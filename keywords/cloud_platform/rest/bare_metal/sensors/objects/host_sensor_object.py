"""Object class for host sensor."""


class HostSensorObject:
    """Represents a host sensor."""

    def __init__(self):
        """Initialize HostSensorObject."""
        self.uuid: str = None
        self.sensorname: str = None
        self.status: str = None

    def set_uuid(self, uuid: str):
        """Set the UUID.

        Args:
            uuid (str): The sensor UUID.
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """Get the UUID.

        Returns:
            str: The sensor UUID.
        """
        return self.uuid

    def set_sensorname(self, sensorname: str):
        """Set the sensor name.

        Args:
            sensorname (str): The sensor name.
        """
        self.sensorname = sensorname

    def get_sensorname(self) -> str:
        """Get the sensor name.

        Returns:
            str: The sensor name.
        """
        return self.sensorname

    def set_status(self, status: str):
        """Set the status.

        Args:
            status (str): The sensor status.
        """
        self.status = status

    def get_status(self) -> str:
        """Get the status.

        Returns:
            str: The sensor status.
        """
        return self.status
