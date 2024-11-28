from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger


class DcManagerTableParser:
    """
    Class for DcManager table parsing.
    This class typically parses the output of a command like 'dcmanager subcloud list', as shown in the table below.

    +----+-----------+------------+--------------+---------------+---------+---------------+-----------------+
    | id | name      | management | availability | deploy status | sync    | backup status | prestage status |
    +----+-----------+------------+--------------+---------------+---------+---------------+-----------------+
    |  5 | subcloud3 | managed    | online       | complete      | in-sync | None          | None            |
    |  6 | subcloud2 | managed    | online       | complete      | in-sync | None          | None            |
    |  7 | subcloud1 | managed    | online       | complete      | in-sync | None          | None            |
    +----+-----------+------------+--------------+---------------+---------+---------------+-----------------+

    """

    def __init__(self, dcmanager_output):
        self.dcmanager_output = dcmanager_output

    def get_output_values_list(self) -> list:
        """
        Getter for output values list
        Returns: the output values list (list(dict[str, str])): each item in this list is a dictionary where the key
        corresponds to a column from the table above, and the value is the content of the cell formed by this column
        and a specific row.

        """
        headers = []
        output_values_list = []
        found_headers = False
        for line in self.dcmanager_output:
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
                        get_logger().log_error(f"Number of headers was {len(headers)} but the number of values was {len(values)}. Full output was {self.dcmanager_output}.")
                        raise KeywordException("Number of headers and values do not match")
                    index = 0
                    for header in headers:
                        # create dictionary with header and value
                        output_values[header.strip()] = values[index].strip()
                        index = index + 1
                    output_values_list.append(output_values)
        return output_values_list
