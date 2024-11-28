class IPMIToolSensorObject:
    """
    Class that represents a single row of values from the table displayed as a result of executing the command
    `ipmitool sensor`.
    """

    def __init__(self):
        self.sensor_name = None
        self.current_reading = None
        self.unit_of_measurement = None
        self.operational_status = None
        self.lower_non_recoverable = None
        self.lower_critical = None
        self.lower_non_critical = None
        self.upper_non_critical = None
        self.upper_critical = None
        self.upper_non_recoverable = None

    def set_sensor_name(self, sensor_name: str):
        """
        Setter for the sensor_name
        """
        self.sensor_name = sensor_name

    def get_sensor_name(self) -> str:
        """
        Getter for the sensor_name
        """
        return self.sensor_name

    def set_current_reading(self, current_reading: str):
        """
        Setter for the current_reading
        """
        self.current_reading = current_reading

    def get_current_reading(self) -> str:
        """
        Getter for the current_reading
        """
        return self.current_reading

    def set_unit_of_measurement(self, unit_of_measurement: str):
        """
        Setter for the unit_of_measurement
        """
        self.unit_of_measurement = unit_of_measurement

    def get_unit_of_measurement(self) -> str:
        """
        Getter for the unit_of_measurement
        """
        return self.unit_of_measurement

    def set_operational_status(self, operational_status: str):
        """
        Setter for the operational_status
        """
        self.operational_status = operational_status

    def get_operational_status(self) -> str:
        """
        Getter for the operational_status
        """
        return self.operational_status

    def set_lower_non_recoverable(self, lower_non_recoverable: str):
        """
        Setter for the lower_non_recoverable
        """
        self.lower_non_recoverable = lower_non_recoverable

    def get_lower_non_recoverable(self) -> str:
        """
        Getter for the lower_non_recoverable
        """
        return self.lower_non_recoverable

    def set_lower_critical(self, lower_critical: str):
        """
        Setter for the lower_critical
        """
        self.lower_critical = lower_critical

    def get_lower_critical(self) -> str:
        """
        Getter for the lower_critical
        """
        return self.lower_critical

    def set_lower_non_critical(self, lower_non_critical: str):
        """
        Setter for the lower_non_critical
        """
        self.lower_non_critical = lower_non_critical

    def get_lower_non_critical(self) -> str:
        """
        Getter for the lower_non_critical
        """
        return self.lower_non_critical

    def set_upper_non_critical(self, upper_non_critical: str):
        """
        Setter for the upper_non_critical
        """
        self.upper_non_critical = upper_non_critical

    def get_upper_non_critical(self) -> str:
        """
        Getter for the upper_non_critical
        """
        return self.upper_non_critical

    def set_upper_critical(self, upper_critical: str):
        """
        Setter for the upper_critical
        """
        self.upper_critical = upper_critical

    def get_upper_critical(self) -> str:
        """
        Getter for the upper_critical
        """
        return self.upper_critical

    def set_upper_non_recoverable(self, upper_non_recoverable: str):
        """
        Setter for the upper_non_recoverable
        """
        self.upper_non_recoverable = upper_non_recoverable

    def get_upper_non_recoverable(self) -> str:
        """
        Getter for the upper_non_recoverable
        """
        return self.upper_non_recoverable
