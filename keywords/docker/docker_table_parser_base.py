from typing import List

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.docker.docker_table_parser_header import DockerTableParserHeader


class DockerTableParserBase:
    """
    Base Class for parsing the output of Table-Like Docker commands.
    This class shouldn't be used directly. Instead, it should be inherited by specific docker table parser implementations.
    See DockerImagesTableParser as an example.
    """

    def __init__(self, docker_output):
        """
        Constructor
        Args:
            docker_output: The raw String output of a docker command that returns a table.
        """
        self.docker_output = docker_output
        self.possible_headers = []  # This needs to be defined in child classes of DockerTableParser

    def get_output_values_list(self):
        """
        This function will take the raw String output of a docker command that returns a table
        and will parse it into a list of dictionaries. For example, if self.docker_output is:

        REPOSITORY                          TAG         IMAGE ID        CREATED         SIZE
        alpine                              latest      1d34ffeaf190    4 weeks ago     7.79MB
        busybox                             latest      65ad0d468eb1    13 months ago   4.26MB
        registry.local:9001/node-hello      latest      4c7ea8709739    8 years ago     644MB

        then the function will return:

        [{'REPOSITORY': 'alpine', 'TAG': 'latest', 'IMAGE ID': '1d34ffeaf190', 'CREATED': '4 weeks ago', 'SIZE': '7.79MB'},
         {'REPOSITORY': 'busybox', 'TAG': 'latest', 'IMAGE ID': '65ad0d468eb1', 'CREATED': '13 months ago', 'SIZE': '4.26MB'},
         {'REPOSITORY': 'registry.local:9001/node-hello', 'TAG': 'latest', 'IMAGE ID': '4c7ea8709739', 'CREATED': '8 years ago', 'SIZE': '644MB'}]

        """
        if not self.possible_headers:
            get_logger().log_error("There are no 'possible_headers' defined. Please use the specific child class of the docker_table_parser that has the headers that you need.")
            raise KeywordException("Undefined 'possible_headers'.")

        headers = []
        output_values_list = []
        found_headers = False

        for line in self.docker_output:
            if not found_headers:
                # Handle Headers.
                found_headers = True
                headers = self.get_headers(line)

            else:

                # Handle entry detail lines.
                line = line.rstrip("\n")
                if ':~$' in line:  # this would be a prompt and we want to skip it
                    continue

                output_values = {}
                for header in headers:
                    value = line[header.get_start_position() : header.get_end_position()]
                    output_values[header.get_name()] = value.strip()

                output_values_list.append(output_values)

        return output_values_list

    def get_headers(self, line: str) -> List[DockerTableParserHeader]:
        """
        This function will extract the headers from the header line passed in.
        Args:
            line: Line containing all the headers to be parsed.

        Returns: List of DockerTableParserHeader that have been found, in order.

        """
        headers = []
        line = f"{line}\n"
        # Find all the known headers.
        for header in self.possible_headers:
            if header in line:

                # Find the header followed by a space or end of line.
                # This is to avoid headers that are substrings of other headers.
                header_index = line.find(header + " ")
                header_index_last = line.find(header + "\n")
                index = max(header_index, header_index_last)

                header_in_line = DockerTableParserHeader(header, index)
                headers.append(header_in_line)

        # Sort the headers by reverse order in the line.
        headers.sort(key=lambda x: x.get_start_position(), reverse=True)

        # Fill in the end_position of the Header objects.
        next_header_start = max([len(line) for line in self.docker_output])  # End of the longest line.
        for header in headers:
            header.set_end_position(next_header_start)
            next_header_start = header.get_start_position()

        # Sort the headers by order in the line.
        headers.sort(key=lambda x: x.get_start_position(), reverse=True)

        return headers
