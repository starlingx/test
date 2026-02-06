from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger


class KubeCpusetsTableParser:
    """Parser for kube-cpusets table output.

    Sample Table:
    '+-----------------------------+--------------------+-------------------+\n'
    '| namespace                   | pod.name           | container.name    |\n'
    '+-----------------------------+--------------------+-------------------+\n'
    '| cert-manager                | cm-cert-manager    | cert-manager      |\n'
    '| kernel-module-management    | kmm-operator       | manager           |\n'
    '+-----------------------------+--------------------+-------------------+\n'
    """

    def __init__(self, table_output: str):
        """Initialize parser.

        Args:
            table_output (str): Table output string.
        """
        self.table_output = table_output

    def get_output_values_list(self) -> list:
        """Parse table and return list of dictionaries.

        Returns:
            list: List of dictionaries with header:value pairs.
        """
        headers = []
        output_values_list = []
        last_output_value = None

        is_in_headers_block = False
        is_in_content_block = False
        number_of_columns = -1

        for line in self.table_output.split("\n"):
            # Skip lines that don't start with | or contain +--
            if not (line.startswith("|") or "+--" in line):
                continue

            # Separator line with +-- indicates state transitions
            if "+--" in line:
                if not is_in_headers_block and not is_in_content_block:
                    # First separator: entering header block
                    is_in_headers_block = True
                    is_in_content_block = False
                    number_of_columns = line.count("+") - 1
                    headers = [""] * number_of_columns
                    continue
                elif is_in_headers_block and not is_in_content_block:
                    # Second separator: leaving header block, entering content block
                    is_in_headers_block = False
                    is_in_content_block = True
                    continue
                else:
                    # Third separator: end of table
                    is_in_headers_block = False
                    is_in_content_block = False

            # Parse header lines (may span multiple lines)
            if is_in_headers_block:
                headers_line = line.split("|")[1:-1]
                if len(headers_line) != number_of_columns:
                    get_logger().log_error(f"Number of headers should be {number_of_columns} but was {len(headers_line)}")
                    raise KeywordException("Number of headers and + separator do not match")

                # Concatenate multi-line headers
                for i in range(number_of_columns):
                    headers[i] += headers_line[i].strip()

            # Parse content lines (may span multiple lines for long values)
            if is_in_content_block:
                values_line = line.split("|")[1:-1]
                if len(values_line) != number_of_columns:
                    get_logger().log_error(f"Number of values should be {number_of_columns} but was {len(values_line)}")
                    raise KeywordException("Number of headers and values do not match")

                # If first column has content, this is a new row
                if values_line[0].strip():
                    last_output_value = {}
                    for i in range(number_of_columns):
                        last_output_value[headers[i]] = values_line[i].strip()
                    output_values_list.append(last_output_value)
                else:
                    # First column empty means continuation of previous row
                    for i in range(number_of_columns):
                        last_output_value[headers[i]] += values_line[i].strip()

        return output_values_list
