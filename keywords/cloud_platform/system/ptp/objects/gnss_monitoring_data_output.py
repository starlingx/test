import re
from typing import Union

from keywords.cloud_platform.system.ptp.objects.gnss_monitoring_data_object import GnssMonitoringDataObject


class GnssMonitoringDataOutput:
    """
    This class parses GNSS monitoring CLI tool output and creates GnssMonitoringDataObject instances.
    """

    def __init__(self, cli_output: Union[str, list[str]]):
        """
        Initialize with CLI tool output.

        Args:
            cli_output (Union[str, list[str]]): Output from GNSS monitoring CLI tool.
        """
        self.raw_output = cli_output
        self.monitoring_data = self._parse_monitoring_data()

    def _parse_monitoring_data(self) -> list[GnssMonitoringDataObject]:
        """
        Parse the CLI output and create monitoring data objects.

        Returns:
            list[GnssMonitoringDataObject]: List of parsed monitoring data objects.
        """
        monitoring_data = []

        # Convert to string if it's a list
        if isinstance(self.raw_output, list):
            output_text = "\n".join(self.raw_output)
        else:
            output_text = self.raw_output

        # Parse device data using regex
        # Example: /dev/ttyACM0's gps_data: GpsData(gpsd_running=1, lock_state=1, satellite_count=21, signal_quality_db=SignalQualityDb(min=42.0, max=47.0, avg=44.571))
        device_pattern = r"(/dev/\w+)'s gps_data: GpsData\(gpsd_running=(\d+), lock_state=(\d+), satellite_count=(\d+), signal_quality_db=SignalQualityDb\(min=([\d.]+), max=([\d.]+), avg=([\d.]+)\)\)"

        matches = re.findall(device_pattern, output_text)

        for match in matches:
            device_path, gpsd_running, lock_state, satellite_count, sig_min, sig_max, sig_avg = match

            data_obj = GnssMonitoringDataObject()
            data_obj.set_device_path(device_path)
            data_obj.set_gpsd_running(int(gpsd_running))
            data_obj.set_lock_state(int(lock_state))
            data_obj.set_satellite_count(int(satellite_count))
            data_obj.set_signal_quality_min(float(sig_min))
            data_obj.set_signal_quality_max(float(sig_max))
            data_obj.set_signal_quality_avg(float(sig_avg))

            monitoring_data.append(data_obj)

        return monitoring_data

    def get_monitoring_data(self) -> list[GnssMonitoringDataObject]:
        """
        Get all monitoring data objects.

        Returns:
            list[GnssMonitoringDataObject]: List of monitoring data objects.
        """
        return self.monitoring_data

    def get_monitoring_data_for_device(self, device_path: str) -> GnssMonitoringDataObject:
        """
        Get monitoring data for a specific device.

        Args:
            device_path (str): Path to the device.

        Returns:
            GnssMonitoringDataObject: Monitoring data for the specified device.

        Raises:
            ValueError: If device not found in monitoring data.
        """
        for data in self.monitoring_data:
            if data.get_device_path() == device_path:
                return data

        raise ValueError(f"Device '{device_path}' not found in monitoring data")
