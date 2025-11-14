from framework.exceptions.keyword_exception import KeywordException


class GnssMonitorConfParser:
    """
    Class for GNSS monitor conf parsing

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
        Constructor

        Args:
            gnss_monitor_conf_output (list[str]): a list of strings representing the output of a 'cat gnss-monitor-ptp.conf' command.
        """
        self.gnss_monitor_conf_output = gnss_monitor_conf_output

    def get_output_values_dict(self) -> dict:
        """
        Getter for output values dict

        Returns:
            dict: the output values dict

        """
        output_values_dict = {}

        for row in self.gnss_monitor_conf_output:
            if "~$" in row or "Password:" in row:
                continue  # these prompts should be ignored

            # Skip empty lines, comments, and section headers
            stripped_row = row.strip()
            if not stripped_row or stripped_row.startswith("#") or stripped_row.startswith("["):
                continue

            # Split on first space to handle values with spaces
            parts = stripped_row.split(None, 1)
            if len(parts) == 2:
                key, value = parts
                output_values_dict[key.strip()] = value.strip()
            elif len(parts) == 1:
                # Handle cases where there might be a key without value
                key = parts[0].strip()
                if key:
                    output_values_dict[key] = ""
            else:
                raise KeywordException(f"Line with values: {row} was not in the expected format")

        return output_values_dict
