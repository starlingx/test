import re

from framework.exceptions.keyword_exception import KeywordException


class SystemVerticalTableParser:
    """
    Class for System vertical table parsing.

    In a vertical table, attributes and their corresponding values are arranged in adjacent columns,
    with each attribute listed alongside its value.

    As an example of a typical argument for the constructor of this class, consider the output of the command
    'system host-show {hostname}':

    +------------------------+----------------------------------------------------------------------+
    | Property               | Value                                                                |
    +------------------------+----------------------------------------------------------------------+
    | action                 | none                                                                 |
    | administrative         | unlocked                                                             |
    | apparmor               | disabled                                                             |
    | availability           | available                                                            |
    | bm_ip                  | None                                                                 |
    | bm_type                | none                                                                 |
    | bm_username            | None                                                                 |
    | boot_device            | /dev/disk/by-path/pci-0000:32:00.0-nvme-1                            |
    | capabilities           | {'is_max_cpu_configurable': 'configurable', 'mgmt_ipsec': 'enabled', |
    |                        | 'stor_function': 'monitor', 'Personality': 'Controller-Active'}      |
    | clock_synchronization  | ntp                                                                  |

    some more configuration properties ...

    | vim_progress_status    | services-enabled                                                     |
    +------------------------+----------------------------------------------------------------------+

    Example of a minimum valid table:
    +------------------------+----------------------------------------------------------------------+
    | Property               | Value                                                                |
    +------------------------+----------------------------------------------------------------------+
    | action                 | none                                                                 |
    +------------------------+----------------------------------------------------------------------+

    There are cases in which the last row is a message that is not part of the table. An example of this case is
    shown below.
    +---------------+----------------------------------+
    | Property      | Value                            |
    +---------------+----------------------------------+
    | active        | True                             |
    | app_version   | 0.1.0                            |
    | created_at    | 2024-10-16T14:58:17.305376+00:00 |
    | manifest_file | fluxcd-manifests                 |
    | manifest_name | hello-kitty-fluxcd-manifests     |
    | name          | hello-kitty                      |
    | progress      | None                             |
    | status        | removing                         |
    | updated_at    | 2024-10-16T15:50:59.902779+00:00 |
    +---------------+----------------------------------+
    Please use 'system application-list' or 'system application-show hello-kitty' to view the current progress.

    """

    _MIN_ROWS = 5

    def __init__(self, system_output: list[str] | str):
        """
        Constructor.

        Args:
            system_output (list[str] | str): a list of strings or a string representing the output of a 'system <*>' command.
        """
        self.system_output = system_output

    def get_output_values_dict(
        self,
    ):
        """
        Getter for output values dict.

        Returns: the output values dict

        """
        # Regex to validate the pattern "+---+---+", with varying dashes
        pattern = r"^\+\-+\+\-+\+$"

        # Get the total number of rows.
        total_rows = len(self.system_output)

        # If there are fewer than two rows, the table is not valid.
        if total_rows < SystemVerticalTableParser._MIN_ROWS:
            raise KeywordException("It is expected that a table have at least " f"{SystemVerticalTableParser._MIN_ROWS} rows. Found {total_rows} rows.")

        # Check if the first row matches the pattern.
        first_row_valid = re.match(pattern, self.system_output[0])

        # Check if the third row matches the pattern.
        third_row_valid = re.match(pattern, self.system_output[2])

        # Check if the last row matches the pattern.
        last_row_valid = re.match(pattern, self.system_output[total_rows - 1])

        # Check if the second-to-last row matches the pattern.
        second_last_row_valid = re.match(pattern, self.system_output[total_rows - 2])

        # Check if there is some text in the last different from the pattern.
        has_text_in_last_row = True if not last_row_valid and self.system_output[total_rows - 1].strip() != "" else False

        # There are cases in which the last row is a message that is not part of the table.
        # Refer to the header comment of this class for an example.
        if not last_row_valid:
            if not second_last_row_valid or not has_text_in_last_row:
                raise KeywordException("It is expected that a table have exactly two columns.")

        # In any case the first and third rows must be valid rows.
        if not first_row_valid or not third_row_valid:
            raise KeywordException("It is expected that a table have exactly two columns.")

        # The headers must contain the texts 'Property' and 'Value'.
        if not str(self.system_output[1]).__contains__("Property") or not str(self.system_output[1]).__contains__("Value"):
            raise KeywordException("It is expected that a table have a header with 'Property' and 'Value' labels.")

        # The last row can be last element in 'self.system_output' or the second-last element in 'self.system_output'.
        last_row = total_rows - 1
        if not last_row_valid and second_last_row_valid and has_text_in_last_row:
            last_row = total_rows - 2

        output_values_dict = {}

        data_row_number = 0
        previous_key = None
        for row in self.system_output[3:last_row]:  # Ignore the first three rows and the last row.

            # Detect regex syntax patterns
            regex_indicators = ["regexp:", "regex:", r"\^/", r"\$\|/", r"\([^)]*\|[^)]*\)"]  # Explicit regex keywords  # Start anchor with path  # End anchor with pipe  # Parentheses containing pipes

            if "!!binary" in row:
                row = row.replace("!!binary |", "")

            has_regex = any(re.search(pattern, str(row)) for pattern in regex_indicators)
            if not has_regex and str(row).count("|") != 3:
                raise KeywordException("It is expected that a table have exactly two columns.")

            parts = row.split("|")

            if len(parts) > 2:
                key = parts[1].strip()
                value = parts[2].strip()
                if key:
                    output_values_dict[key] = value
                    previous_key = key
                else:
                    # This 'else' block handles cases where the property name spans multiple lines, ensuring proper parsing.
                    if data_row_number == 0:
                        raise KeywordException("The property name in the first data row cannot be empty.")
                    output_values_dict[previous_key] = output_values_dict[previous_key] + " " + value
            data_row_number += 1

        return output_values_dict
