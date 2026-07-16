from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger


class SystemTableParser:
    """
    Class for System table parsing

    Sample Table:
    '+--------------------------------------+---------+-----------+---------------+\n'
    '| uuid                                 | name    | ptp_insta | parameters    |\n'
    '|                                      |         | nce_name  |               |\n'
    '+--------------------------------------+---------+-----------+---------------+\n'
    "| 0000c96e-6dab-48c2-875a-48af194c893c | n4_p2   | ptp4      | ['masterOnly= |\n"
    "|                                      |         |           | 1']           |\n"
    '|                                      |         |           |               |\n'
    '| 24003e49-f9c4-4794-970e-506fa5c215c0 | n1_if   | clock1    | []            |\n'
    '| 51e06821-b045-4a6e-854b-6bd829b5c9e2 | ptp1if1 | ptp1      | []            |\n'
    "| a689d398-329f-46b4-a99f-23b9a2417c27 | n5_p2   | ptp5      | ['masterOnly= |\n"
    "|                                      |         |           | 1']           |\n"
    '|                                      |         |           |               |\n'
    '+--------------------------------------+---------+-----------+---------------+\n'
    """

    def __init__(self, system_output):
        self.system_output = system_output

    def _split_row_by_boundaries(self, line: str, boundaries: list[int]) -> list[str]:
        """Split a table row into cell values using fixed column boundary positions.

        The positions of the '+' characters in the separator line
        ('+----+----+') mark exactly where the '|' column delimiters sit in
        every header and content row. Splitting at those fixed positions
        (instead of naively splitting on every '|') means a '|' that appears
        inside a cell value - for example a regex like
        '(2[5-7]\\.\\d+|[1-12]\\d+\\.\\d+)' in an application's progress column -
        no longer corrupts the parse.

        The boundaries are stored relative to the first delimiter, and each row
        is anchored at its own first '|'. This keeps the parse robust even when
        a line carries a leading prefix (e.g. an ANSI escape sequence or shell
        echo) that the other lines do not.

        Args:
            line (str): A single header or content row from the table.
            boundaries (list[int]): Column delimiter offsets relative to the
                first delimiter, derived from the '+' positions in the
                separator line.

        Returns:
            list[str]: The cell values between consecutive boundaries, or an
                empty list if the row's delimiters do not align with the
                boundaries (i.e. a malformed table).
        """
        # Only strip the trailing newline; internal spacing must be preserved
        # so that character positions stay aligned with the separator line.
        stripped_line = line.rstrip("\n")

        # Anchor at the row's own first '|' so a leading prefix on any single
        # line does not throw off the column alignment.
        if "|" not in stripped_line:
            return []
        offset = stripped_line.index("|")

        # A well-formed row must have a '|' at every column boundary position.
        for boundary in boundaries:
            position = offset + boundary
            if position >= len(stripped_line) or stripped_line[position] != "|":
                return []

        values = []
        for i in range(len(boundaries) - 1):
            start = offset + boundaries[i] + 1
            end = offset + boundaries[i + 1]
            values.append(stripped_line[start:end])

        return values

    def get_output_values_list(self) -> list[dict[str, str]]:
        """Getter for output values list.

        Returns:
            list[dict[str, str]]: the output values list

        Sample Output:
            t[0][n] => row '0' column 'n'  => header[n]
            t[1][n] => row '1' column 'n'  => row[1]column[n]

            {
                header[0]: row[1]column[0]
                header[1]: row[1]column[1]
                ...
                header[n]: row[1]column[n]
            }
            ->
            {
                header[0]: row[2]column[0]
                header[1]: row[2]column[1]
                ...
                header[n]: row[2]column[n]
            }
            ...
            ->
            {
                header[0]: row[m]column[0]
                header[1]: row[m]column[1]
                ...
                header[n]: row[m]column[n]
            }
        """
        headers: list[str] = []
        output_values_list: list[dict[str, str]] = []
        last_output_value: dict[str, str] = {}

        is_in_headers_block = False
        is_in_content_block = False
        number_of_columns = -1
        column_boundaries: list[int] = []

        for line in self.system_output:

            # Skip lines that aren't part of the table.
            if not (line.startswith("|") or line.__contains__("+--")):
                continue

            # We have hit a separator which enters Headers, Content, or Ends the table
            if line.__contains__("+--"):

                # Find out in which part of the table we are, based on the "+----" separator.
                if not is_in_headers_block and not is_in_content_block:  # First separator -> Enter Headers
                    is_in_headers_block = True
                    is_in_content_block = False
                    # Record the '+' positions relative to the first '+' - these
                    # are the exact column delimiter offsets used to split every
                    # row, so a '|' inside a cell value does not corrupt the
                    # parse and a leading prefix on the separator line is ignored.
                    separator_line = line.rstrip("\n")
                    first_delimiter = separator_line.index("+")
                    column_boundaries = [index - first_delimiter for index, character in enumerate(separator_line) if character == "+"]
                    number_of_columns = len(column_boundaries) - 1
                    headers = [""] * number_of_columns
                    continue  # This is a separator line, don't try to parse anything.
                elif is_in_headers_block and not is_in_content_block:  # Second separator -> Go to Content
                    is_in_headers_block = False
                    is_in_content_block = True
                    continue  # This is a separator line, don't try to parse anything.
                else:  # Last separator -> The table is complete
                    is_in_headers_block = False
                    is_in_content_block = False

            # Build the list of headers, which could be multi-lined.
            if is_in_headers_block:
                headers_line = self._split_row_by_boundaries(line, column_boundaries)
                if len(headers_line) != number_of_columns:
                    get_logger().log_error(f"Number of headers should be {number_of_columns} based on the number of '+' but the number of values was {len(headers_line)}.")
                    raise KeywordException("Number of headers and + separator do not match expected value")

                for i in range(number_of_columns):
                    headers[i] += headers_line[i].strip()

            # Build the list of values, which could be multi-lined.
            if is_in_content_block:
                values_line = self._split_row_by_boundaries(line, column_boundaries)
                if len(values_line) != number_of_columns:
                    get_logger().log_error(f"Number of values should be {number_of_columns} based on the number of '+' but the number of values was {len(values_line)}.")
                    raise KeywordException("Number of headers and values do not match expected value")

                # If there is a value in the first column, then this is a new entry.
                if values_line[0].strip():

                    # Build a dictionary of the Header:Value
                    last_output_value = {}
                    for i in range(number_of_columns):
                        last_output_value[headers[i]] = values_line[i].strip()
                    output_values_list.append(last_output_value)

                else:  # Otherwise, this is the continuation of the previous line.
                    for i in range(number_of_columns):
                        last_output_value[headers[i]] += values_line[i].strip()

        return output_values_list
