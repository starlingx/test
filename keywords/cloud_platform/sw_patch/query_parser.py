"""Module for parsing software patch query output."""

import re

from framework.exceptions.keyword_exception import KeywordException


class SwPatchQueryParser:
    """Parses output from the `sw-patch query` command."""

    def __init__(self, output_list):
        """Initializes the parser with raw output lines.

        Args:
            output_list (list): List of strings representing command output.
        """
        self.out_lines = output_list

    def parse_data(self):
        """Parses the output and returns a list of dictionaries.

        Returns:
            list[dict]: List of dictionaries containing parsed patch data.
        """
        if len(self.out_lines) < 2:  # Check if there are at least header and one data row
            return []  # Return empty list if no data

        header_line = self.out_lines[0]
        data_lines = self.out_lines[2:]  # Skip the separator line

        header_names = [h.strip() for h in re.split(r"\s{2,}", header_line) if h.strip()]

        parsed_data = []
        for line in data_lines:
            if line.strip('\n'):
                values = [v.strip() for v in re.split(r"\s{2,}", line) if v.strip()]
                if len(values) == len(header_names):
                    parsed_data.append(dict(zip(header_names, values)))
                else:
                    raise KeywordException("Number of headers and values do not match")
        return parsed_data

    def to_list_of_dicts(self):
        """Converts parsed data into a list of dictionaries.

        Returns:
            list[dict]: List of dictionaries representing parsed patches.
        """
        return self.parse_data()
