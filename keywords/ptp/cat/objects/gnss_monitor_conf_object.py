class GnssMonitorConfObject:
    """
    Object to hold the values of GNSS Monitor conf Object
    """

    def __init__(self):
        self.devices: str = ""
        self.satellite_count: int = 0
        self.signal_quality_db: int = 0

    def set_devices(self, devices: str):
        """
        Setter for devices

        Args:
            devices (str): the devices

        """
        self.devices = devices

    def get_devices(self) -> str:
        """
        Getter for devices

        Returns:
            str: the devices

        """
        return self.devices

    def set_satellite_count(self, satellite_count: int):
        """
        Setter for satellite_count

        Args:
            satellite_count (int): the satellite_count

        """
        self.satellite_count = satellite_count

    def get_satellite_count(self) -> int:
        """
        Getter for satellite_count

        Returns:
            int: the satellite_count

        """
        return self.satellite_count

    def set_signal_quality_db(self, signal_quality_db: int):
        """
        Setter for signal_quality_db

        Args:
            signal_quality_db (int): the signal_quality_db

        """
        self.signal_quality_db = signal_quality_db

    def get_signal_quality_db(self) -> int:
        """
        Getter for signal_quality_db

        Returns:
            int: the signal_quality_db

        """
        return self.signal_quality_db
