class IPMIToolTableParser:
    """
    Class for IPMITool table parsing
    """

    def __init__(self, openstack_output):
        self.openstack_output = openstack_output

    def get_output_values_list(self):
        """
        Getter for output values list
        Returns: the output values list

        """

        output_values = {}
        for line in self.openstack_output:
            # Actual output have : separators
            if line.__contains__(':'):
                values = line.split(':')
                output_values[values[0].strip()] = values[1].strip()

        return output_values
