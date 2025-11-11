from keywords.ptp.cat.gnss_monitor_conf_parser import GnssMonitorConfParser
from keywords.ptp.cat.objects.gnss_monitor_conf_object import GnssMonitorConfObject


class GnssMonitorConfOutput:
    """
    This class parses the output of cat GNSS monitor conf file

    Example:
        [global]
        ##
        ## Default Data Set
        ##
        devices /dev/ttyACM0 /dev/gnssx
        satellite_count 8
        signal_quality_db 30

    """

    def __init__(self, gnss_monitor_conf_output: list[str]):
        """
        Create an internal GnssMonitorConfObject from the passed parameter.

        Args:
            gnss_monitor_conf_output (list[str]): a list of strings representing the GNSS monitor conf output

        """
        gnss_monitor_conf_parser = GnssMonitorConfParser(gnss_monitor_conf_output)
        output_values = gnss_monitor_conf_parser.get_output_values_dict()

        self.gnss_monitor_conf_object = GnssMonitorConfObject()

        if "devices" in output_values:
            self.gnss_monitor_conf_object.set_devices(output_values["devices"])

        if "satellite_count" in output_values:
            self.gnss_monitor_conf_object.set_satellite_count(int(output_values["satellite_count"]))

        if "signal_quality_db" in output_values:
            self.gnss_monitor_conf_object.set_signal_quality_db(int(output_values["signal_quality_db"]))

    def get_gnss_monitor_conf_object(self) -> GnssMonitorConfObject:
        """
        Getter for GnssMonitorConfObject.

        Returns:
            GnssMonitorConfObject: The GnssMonitorConfObject

        """
        return self.gnss_monitor_conf_object
