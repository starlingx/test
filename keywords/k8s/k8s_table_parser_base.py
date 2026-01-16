import re
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

    def __init__(self, k8s_output: str):
        """
        Constructor.

        Args:
            k8s_output (str): The raw String output of a kubernetes command that returns a table.
        """
        self.k8s_output = k8s_output
        self.possible_headers = []  # This needs to be defined in child classes of K8sTableParser

    def get_output_values_list(self):
        """
        Parse kubernetes table output into a list of dictionaries.

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
        Extract the headers from the header line passed in.

        Args:
            line (str): Line containing all the headers to be parsed.

        Returns:
            List[K8sTableParserHeader]: List of K8sTableParserHeader that have been found, in order.
        """
        headers = []

        # Find all known headers in the line and record their positions
        for header in self.possible_headers:
            if header in line:
                # Escape special regex characters (e.g., parentheses in "PORT(S)")
                # Use word boundaries (\b) only for alphanumeric headers to prevent substring matches
                # For headers with special chars like "PORT(S)", word boundaries don't work properly
                # Example: "NAME" needs \b to avoid matching "NAMESPACE", but "PORT(S)" cannot use \b
                if header[0].isalnum() and header[-1].isalnum():
                    pattern = rf"\b{re.escape(header)}\b"
                else:
                    pattern = re.escape(header)

                match = re.search(pattern, line)
                if match:
                    # Get the starting position of the header in the line
                    header_index = match.start()
                    # Check if header is at the end of the line (followed by newline)
                    header_index_last = line.find(header + "\n")
                    # Use the maximum of both indices to handle edge cases
                    index = max(header_index, header_index_last)
                    header_in_line = K8sTableParserHeader(header, index)
                    headers.append(header_in_line)

        # Sort headers by position in reverse order for end position calculation
        headers.sort(key=lambda x: x.get_start_position(), reverse=True)

        # Calculate end positions for each header
        # The end position of a header is the start position of the next header
        # For the last header, use the length of the longest line in the output
        next_header_start = max([len(line) for line in self.k8s_output])  # End of the longest line.
        for header in headers:
            header.set_end_position(next_header_start)
            next_header_start = header.get_start_position()

        # Sort headers back to their natural order (left to right)
        headers.sort(key=lambda x: x.get_start_position(), reverse=True)
        # Validate that we caught all the headers.
        # Make sure that we didn't accidentally pick of other headers in the "start-end" blocks.
        for header in headers:
            header_line_block = line[header.get_start_position() : header.get_end_position()]
            if header_line_block.strip() != header.get_name():
                # Found an unexpected header that's not in possible_headers list
                missed_header = header_line_block.replace(header.get_name(), "").strip()
                raise NotImplementedError(f"Header Missing: {missed_header} must be added to the list of possible_headers.")

        return headers
