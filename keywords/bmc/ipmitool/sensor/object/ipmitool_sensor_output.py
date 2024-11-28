from keywords.bmc.ipmitool.ipmitool_sensor_table_parser import IPMIToolSensorTableParser
from keywords.bmc.ipmitool.sensor.object.ipmitool_sensor_object import IPMIToolSensorObject


class IPMIToolSensorOutput:
    """
    IMPITool Sensor Output
    """

    def __init__(self, ipmitool_output):
        """
        Constructor
        This constructor receives a list of strings, resulting from the execution of the command `ipmitool sensor`, and
        generates a list of `IPMIToolSensorObject` objects.

        Args:
            ipmitool_output: list of strings resulting from the execution of the command `ipmitool sensor`.

        Note: The command `ipmitool sensor` is executed with `sudo -S`. This results in the string "Password: " being
        printed on the same line as the command result. That's why this constructor removes this 'extra' string as the
        first step.

        """
        # Removes the string "Password:" from the first line if this string is present.
        if len(ipmitool_output) > 0:
            first_line = ipmitool_output[0]
            new_first_line = first_line[len("Password:") :] if first_line.startswith("Password: ") else first_line
            ipmitool_output[0] = new_first_line

        ipmitool_sensor_table_parser = IPMIToolSensorTableParser(ipmitool_output)
        output_values = ipmitool_sensor_table_parser.get_output_values_list()
        self.ipmitool_sensor_objects: list[IPMIToolSensorObject] = []

        for item_list in output_values:
            ipmitool_sensor_object = IPMIToolSensorObject()
            ipmitool_sensor_object.sensor_name = item_list["sensor_name"]
            ipmitool_sensor_object.current_reading = item_list["current_reading"]
            ipmitool_sensor_object.unit_of_measurement = item_list["unit_of_measurement"]
            ipmitool_sensor_object.operational_status = item_list["operational_status"]
            ipmitool_sensor_object.lower_non_recoverable = item_list["lower_non_recoverable"]
            ipmitool_sensor_object.lower_critical = item_list["lower_critical"]
            ipmitool_sensor_object.lower_non_critical = item_list["lower_non_critical"]
            ipmitool_sensor_object.upper_non_critical = item_list["upper_non_critical"]
            ipmitool_sensor_object.upper_critical = item_list["upper_critical"]
            ipmitool_sensor_object.upper_non_recoverable = item_list["upper_non_recoverable"]
            self.ipmitool_sensor_objects.append(ipmitool_sensor_object)

    def get_ipmitool_sensor_list(self):
        """
        Gets the list of `IPMIToolSensorObject` objects.
        Args: none.

        Returns:
            The list of `IPMIToolSensorObject` objects.

        """
        return self.ipmitool_sensor_objects
