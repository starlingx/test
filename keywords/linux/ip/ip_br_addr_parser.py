import re


class IPBrAddrParser:
    """
    Class to parse the output of the 'ip -br addr' command execution.
    """

    def __init__(self, ip_br_addr_output):
        """
        Constructor
        Args:
            ip_br_addr_output (str): a string representing the output of the 'ip -br addr' command execution.
        """
        self.ip_br_addr_output = ip_br_addr_output

    def get_output_values_list(self) -> list[dict]:
        """
        Getter for output values list.

        Args: None.

        Returns:
            list[dict]: the output values list.

        """

        output_values_list: list[dict] = []
        for line in self.ip_br_addr_output:

            # Replaces sequences of spaces with a single space.
            line = re.sub(r'\s+', ' ', line)

            # Removes the prefix '\x1b[?2004l' from the beginning of a line.
            line = line.removeprefix('\x1b[?2004l')

            # Removes '\n', spaces, etc at end of each line.
            line = line.rstrip()

            # Does not consider the line containing the executed command.
            if line == "ip -br addr":
                continue

            values = line.split(' ')
            output_values = {}
            if len(values) >= 1:
                output_values['network_interface_name'] = values[0].strip()
            if len(values) >= 2:
                output_values['network_interface_status'] = values[1].strip()
            if len(values) >= 3:
                output_values['ip_addresses'] = values[2:-1]
            if len(output_values) >= 0:
                output_values_list.append(output_values)
        return output_values_list
