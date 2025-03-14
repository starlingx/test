from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger


class FaultManagementTableParser:
    """
    Class for Fault Management table parsing
    """

    def __init__(self, fault_management_output):
        self.fault_management_output = fault_management_output

    def get_output_values_list(self):
        """
        Getter for output values list
        Returns: the output values list

        """

        headers = []
        output_values_list = []
        found_headers = False
        for line in self.fault_management_output:
            # output that we care about like headers and actual output have | separators
            if line.__contains__('|'):
                # find the headers first
                if not found_headers:
                    headers = line.split('|')[1:-1]
                    found_headers = True
                else:
                    output_values = {}
                    values = line.split('|')[1:-1]
                    if len(headers) != len(values):
                        get_logger().log_error(f"Number of headers was {len(headers)} " f"but the number of values was {len(values)}. " f"Full output was {self.fault_management_output}")
                        raise KeywordException("Number of headers and values do not match")
                    index = 0
                    for header in headers:
                        # create dictionary with header and value
                        output_values[header.strip()] = values[index].strip()
                        index = index + 1
                    output_values_list.append(output_values)
        return output_values_list
