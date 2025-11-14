class GnssMonitoringDataObject:
    """
    Represents GNSS monitoring data for a single device.
    """

    def __init__(self):
        """
        Initializes a GnssMonitoringDataObject instance.
        """
        self.device_path = None
        self.gpsd_running = None
        self.lock_state = None
        self.satellite_count = None
        self.signal_quality_min = None
        self.signal_quality_max = None
        self.signal_quality_avg = None

    def set_device_path(self, device_path: str):
        """
        Setter for device path.

        Args:
            device_path (str): Path to the GNSS device.
        """
        self.device_path = device_path

    def get_device_path(self) -> str:
        """
        Getter for device path.

        Returns:
            str: Path to the GNSS device.
        """
        return self.device_path

    def set_gpsd_running(self, gpsd_running: int):
        """
        Setter for gpsd running status.

        Args:
            gpsd_running (int): GPSD running status (1 for running, 0 for not running).
        """
        self.gpsd_running = gpsd_running

    def get_gpsd_running(self) -> int:
        """
        Getter for gpsd running status.

        Returns:
            int: GPSD running status.
        """
        return self.gpsd_running

    def set_lock_state(self, lock_state: int):
        """
        Setter for lock state.

        Args:
            lock_state (int): Lock state (1 for locked, 0 for not locked).
        """
        self.lock_state = lock_state

    def get_lock_state(self) -> int:
        """
        Getter for lock state.

        Returns:
            int: Lock state.
        """
        return self.lock_state

    def set_satellite_count(self, satellite_count: int):
        """
        Setter for satellite count.

        Args:
            satellite_count (int): Number of satellites.
        """
        self.satellite_count = satellite_count

    def get_satellite_count(self) -> int:
        """
        Getter for satellite count.

        Returns:
            int: Number of satellites.
        """
        return self.satellite_count

    def set_signal_quality_min(self, signal_quality_min: float):
        """
        Setter for minimum signal quality.

        Args:
            signal_quality_min (float): Minimum signal quality in dB-Hz.
        """
        self.signal_quality_min = signal_quality_min

    def get_signal_quality_min(self) -> float:
        """
        Getter for minimum signal quality.

        Returns:
            float: Minimum signal quality.
        """
        return self.signal_quality_min

    def set_signal_quality_max(self, signal_quality_max: float):
        """
        Setter for maximum signal quality.

        Args:
            signal_quality_max (float): Maximum signal quality in dB-Hz.
        """
        self.signal_quality_max = signal_quality_max

    def get_signal_quality_max(self) -> float:
        """
        Getter for maximum signal quality.

        Returns:
            float: Maximum signal quality.
        """
        return self.signal_quality_max

    def set_signal_quality_avg(self, signal_quality_avg: float):
        """
        Setter for average signal quality.

        Args:
            signal_quality_avg (float): Average signal quality in dB-Hz.
        """
        self.signal_quality_avg = signal_quality_avg

    def get_signal_quality_avg(self) -> float:
        """
        Getter for average signal quality.

        Returns:
            float: Average signal quality.
        """
        return self.signal_quality_avg
