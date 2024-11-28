from framework.exceptions.keyword_exception import KeywordException


class IPMIToolSensorTableParser:
    """
    Class for IPMITool Sensor table parsing.
    The IPMItool Sensor table is a string formatted as a table, resulting from the execution of the command
    'ipmitool sensor' in a Linux terminal.
    This class receives an IPMITool Sensor table, as shown below, in its constructor and returns a list of dictionaries.
    Each of these dictionaries has the following keys:
        1) sensor_name;
        2) current_reading;
        3) unit_of_measurement;
        4) operational_status;
        5) lower_non_recoverable;
        6) lower_critical;
        7) lower_non_critical;
        8) upper_non_critical;
        9) upper_critical;
        10) upper_non_recoverable.

    A partial example of an IPMITool Sensor table:

    Temp             | 32.000     | degrees C  | ok    | na        | 3.000     | na        | na        | 98.000    | na
    Temp             | 29.000     | degrees C  | ok    | na        | 3.000     | na        | na        | 98.000    | na
    Inlet Temp       | 17.000     | degrees C  | ok    | na        | -7.000    | 3.000     | 38.000    | 42.000    | na
    Fan1A            | 7560.000   | RPM        | ok    | na        | 480.000   | 840.000   | na        | na        | na
    Fan2A            | 7320.000   | RPM        | ok    | na        | 480.000   | 840.000   | na        | na        | na

    Note: 1) The type, name, and amount of sensors can vary dramatically depending on the host.
          2) The table has no headers. We can learn about the headers through the names of the dictionary keys.

    """

    def __init__(self, command_output):
        self.command_output = command_output

    def get_output_values_list(self):
        """
        Getter for output values list.
        Returns: the output values list as a list of dictionaries with the following keys:
            1) sensor_name;
            2) current_reading;
            3) unit_of_measurement;
            4) operational_status;
            5) lower_non_recoverable;
            6) lower_critical;
            7) lower_non_critical;
            8) upper_non_critical;
            9) upper_critical;
            10) upper_non_recoverable.

        """
        if not self.command_output:
            return []

        output_values = []
        for line in self.command_output:

            if str(line).count('|') != 9:
                raise KeywordException("It is expected that a table have exactly ten columns.")

            values = line.split('|')
            list_item = {
                "sensor_name": values[0].strip(),
                "current_reading": values[1].strip(),
                "unit_of_measurement": values[2].strip(),
                "operational_status": values[3].strip(),
                "lower_non_recoverable": values[4].strip(),
                "lower_critical": values[5].strip(),
                "lower_non_critical": values[6].strip(),
                "upper_non_critical": values[7].strip(),
                "upper_critical": values[8].strip(),
                "upper_non_recoverable": values[9].strip(),
            }

            output_values.append(list_item)

        return output_values
