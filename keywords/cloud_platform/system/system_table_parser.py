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

    def get_output_values_list(self):
        """
        Getter for output values list
        Returns: the output values list

        """

        headers = []
        output_values_list = []
        last_output_value = None

        is_in_headers_block = False
        is_in_content_block = False
        number_of_columns = -1

        for line in self.system_output:

            # Skip lines that aren't part of the table.
            if not (line.startswith("|") or line.__contains__("+--")):
                continue

            # We have hit a separator which enters Headers, Content, or Ends the table
            if line.__contains__('+--'):

                # Find out in which part of the table we are, based on the "+----" separator.
                if not is_in_headers_block and not is_in_content_block: # First separator -> Enter Headers
                    is_in_headers_block = True
                    is_in_content_block = False
                    number_of_columns = line.count('+') - 1
                    headers = [""] * number_of_columns
                    continue # This is a separator line, don't try to parse anything.
                elif is_in_headers_block and not is_in_content_block: # Second separator -> Go to Content
                    is_in_headers_block = False
                    is_in_content_block = True
                    continue # This is a separator line, don't try to parse anything.
                else: # Last separator -> The table is complete
                    is_in_headers_block = False
                    is_in_content_block = False

            # Build the list of headers, which could be multi-lined.
            if is_in_headers_block:
                headers_line = line.split('|')[1:-1]
                if len(headers_line) != number_of_columns:
                    get_logger().log_error(f"Number of headers should be {number_of_columns} based on the number of '+' but the number of values was {len(headers_line)}.")
                    raise KeywordException("Number of headers and + separator do not match expected value")

                for i in range(number_of_columns):
                    headers[i] += headers_line[i].strip()

            # Build the list of values, which could be multi-lined.
            if is_in_content_block:
                values_line = line.split('|')[1:-1]
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

                else: # Otherwise, this is the continuation of the previous line.
                    for i in range(number_of_columns):
                        last_output_value[headers[i]] += values_line[i].strip()

        return output_values_list
