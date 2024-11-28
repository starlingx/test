from framework.exceptions.keyword_exception import KeywordException


class DcManagerVerticalTableParser:
    """
    Class for DcManager vertical table parsing
    In a vertical table, attributes and their corresponding values are arranged in adjacent columns,
    with each attribute listed alongside its value.

    As an example of a typical argument for the constructor of this class, consider the output of the command
    'dcmanager subcloud show <cloud name>':

    +-----------------------------+----------------------------------+
    | Field                       | Value                            |
    +-----------------------------+----------------------------------+
    | id                          | 4                                |
    | name                        | subcloud1                        |
    | description                 | None                             |
    | location                    | None                             |
    | software_version            | 24.09                            |
    | management                  | managed                          |
    | availability                | offline                          |
    | deploy_status               | complete                         |
    | management_subnet           | fdff:10:80:221::/64              |
    | management_start_ip         | fdff:10:80:221::2                |
    | management_end_ip           | fdff:10:80:221::ffff             |

    some more configuration properties ...

    | region_name                 | 11a60317384d4eef89c629449d4c2de2 |
    +-----------------------------+----------------------------------+

    """

    def __init__(self, dcmanager_output):
        self.dcmanager_output = dcmanager_output

    def get_output_values_dict(self) -> dict:
        """
        Getter for output values dict
        Returns: the output values dictionary (dict[str, str]): Each item in this dictionary represents a
        single row of the table above, where the key is the content of the first column and the value is the content of
        the second column in that row.

        """
        if str(self.dcmanager_output[0]).count("+") != 3 or str(self.dcmanager_output[2]).count("+") != 3 or str(self.dcmanager_output[-1]).count("+") != 3:
            raise KeywordException("It is expected that a table have exactly two columns.")

        if not str(self.dcmanager_output[1]).__contains__("Field") or not str(self.dcmanager_output[1]).__contains__("Value"):
            raise KeywordException("It is expected that a table have a header with 'Field' and 'Value' labels.")

        output_values_dict = {}

        data_row_number = 0
        previous_key = None
        for line in self.dcmanager_output[3:-1]:  # Ignore the first three lines and the last line.

            if str(line).count('|') != 3:
                raise KeywordException("It is expected that a table have exactly two columns.")

            parts = line.split('|')
            if len(parts) > 2:
                key = parts[1].strip()
                value = parts[2].strip()
                if key:
                    output_values_dict[key] = value
                    previous_key = key
                else:  # Treat the case where the field name occupies more than one line.
                    if data_row_number == 0:
                        raise KeywordException("The field name in the first data row cannot be empty.")
                    output_values_dict[previous_key] = output_values_dict[previous_key] + ' ' + value
            data_row_number += 1

        return output_values_dict
