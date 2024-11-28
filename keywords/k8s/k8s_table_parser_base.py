from typing import List

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.k8s.k8s_table_parser_header import K8sTableParserHeader


class K8sTableParserBase:
    """
    Base Class for parsing the output of Table-Like k8s commands.
    This class shouldn't be used directly. Instead, it should be inherited by specific k8s table parser implementations.
    See KubectlGetPodsTableParser as an example.
    """

    def __init__(self, k8s_output):
        """
        Constructor
        Args:
            k8s_output: The raw String output of a kubernetes command that returns a table.
        """
        self.k8s_output = k8s_output
        self.possible_headers = []  # This needs to be defined in child classes of K8sTableParser

    def get_output_values_list(self):
        """
        This function will take the raw String output of a kubernetes command that returns a table
        and will parse it into a list of dictionaries. For example, if self.k8s_output is:

        NAME                          STATUS   AGE
        armada                        Active   18d
        cert-manager                  Active   18d
        default                       Active   18d

        then the function will return:

        [{'NAME': 'armada', 'STATUS': 'Active', 'AGE': '18d'},
         {'NAME': 'cert-manager', 'STATUS': 'Active', 'AGE': '18d'},
         {'NAME': 'default', 'STATUS': 'Active', 'AGE': '18d'}]

        """

        if not self.possible_headers:
            get_logger().log_error("There are no 'possible_headers' defined. Please use the specific child class of the k8s_table_parser that has the headers that you need.")
            raise KeywordException("Undefined 'possible_headers'.")

        headers = []
        output_values_list = []
        found_headers = False

        for line in self.k8s_output:

            if not found_headers:

                # Handle Headers.
                found_headers = True
                headers = self.get_headers(line)

            else:

                # Handle entry detail lines.
                line = line.rstrip("\n")
                output_values = {}
                for header in headers:
                    value = line[header.get_start_position() : header.get_end_position()]
                    output_values[header.get_name()] = value.strip()

                output_values_list.append(output_values)

        return output_values_list

    def get_headers(self, line: str) -> List[K8sTableParserHeader]:
        """
        This function will extract the headers from the header line passed in.
        Args:
            line: Line containing all the headers to be parsed.

        Returns: List of K8sTableParserHeader that have been found, in order.

        """
        headers = []

        # Find all the known headers.
        for header in self.possible_headers:
            if header in line:

                # Find the header followed by a space or end of line.
                # This is to avoid headers that are substrings of other headers.
                header_index = line.find(header + " ")
                header_index_last = line.find(header + "\n")
                index = max(header_index, header_index_last)

                header_in_line = K8sTableParserHeader(header, index)
                headers.append(header_in_line)

        # Sort the headers by reverse order in the line.
        headers.sort(key=lambda x: x.get_start_position(), reverse=True)

        # Fill in the end_position of the Header objects.
        next_header_start = max([len(line) for line in self.k8s_output])  # End of the longest line.
        for header in headers:
            header.set_end_position(next_header_start)
            next_header_start = header.get_start_position()

        # Sort the headers by order in the line.
        headers.sort(key=lambda x: x.get_start_position(), reverse=True)

        # Validate that we caught all the headers.
        # Make sure that we didn't accidentally pick of other headers in the "start-end" blocks.
        for header in headers:
            header_line_block = line[header.get_start_position() : header.get_end_position()]
            if header_line_block.strip() != header.get_name():
                missed_header = header_line_block.replace(header.get_name(), "").strip()
                raise NotImplementedError(f"Header Missing: {missed_header} must be added to the list of possible_headers.")

        return headers
