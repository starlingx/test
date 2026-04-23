from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger


class OpenStackTableParser:
    """
    Class for System table parsing
    """

    def __init__(self, openstack_output):
        self.openstack_output = openstack_output

    def get_output_values_list(self):
        """Getter for output values list.

        Returns: the output values list
        """
        headers = []
        output_values_list = []
        found_headers = False
        for line in self.openstack_output:
            # output that we care about like headers and actual output have | separators
            if line.__contains__("|"):
                # find the headers first
                if not found_headers:
                    headers = line.split("|")[1:-1]
                    found_headers = True
                else:
                    values = line.split("|")[1:-1]
                    if len(headers) != len(values):
                        get_logger().log_error(f"Number of headers was {len(headers)} " f"but the number of values was {len(values)}. " f"Full output was {self.openstack_output}")
                        raise KeywordException("Number of headers and values do not match")

                    # Check if this is a continuation line (first column empty)
                    if output_values_list and values[0].strip() == "":
                        prev = output_values_list[-1]
                        for i, header in enumerate(headers):
                            val = values[i].strip()
                            if val:
                                prev[header.strip()] = prev.get(header.strip(), "") + val
                    else:
                        output_values = {}
                        for i, header in enumerate(headers):
                            output_values[header.strip()] = values[i].strip()
                        output_values_list.append(output_values)
        return output_values_list
