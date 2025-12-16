from framework.exceptions.keyword_exception import KeywordException


class PMCTableParser:
    """
    Class for PMC table parsing

    Example from get DEFAULT_DATA_SET below
    sending: GET DEFAULT_DATA_SET
    507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT DEFAULT_DATA_SET
        twoStepFlag            1
        slaveOnly              0
        numberPorts            1
        priority1              128
        clockClass             248
        clockAccuracy          0xfe
        offsetScaledLogVariance 0xffff
        priority2              128
        clockIdentity          507c6f.fffe.0b5a4d
        domainNumber           0.

    """

    def __init__(self, pmc_output: list[str]):
        """
        Constructor

        Args:
            pmc_output (list[str]): a list of strings representing the output of a 'pmc' command.
        """
        self.pmc_output = pmc_output

    def get_output_values_dict(self) -> list[dict]:
        """
        Getter for output values dict

        Returns:
            list[dict]: the output values dict (empty dict if no output)

        Raises:
            KeywordException: if a line with values is not in the expected format.
        """
        output_values_dict = {}
        output_values_dict_list = []

        total_rows = len(self.pmc_output)
        if total_rows < 2:
            return [{}]

        for row in self.pmc_output[2:total_rows]:  # Ignore the first 2 rows and the last row (prompt)
            if "~$" in row:
                continue  # this a prompt, we can ignore
            if "RESPONSE MANAGEMENT" in row:  # signifies the start of a different set of values of the same object type.
                output_values_dict_list.append(output_values_dict)
                output_values_dict = {}
                continue
            values = row.split(None, 1)  # split once
            if len(values) == 2:
                key, value = values
                output_values_dict[key.strip()] = value.strip()
            else:
                raise KeywordException(f"Line with values: {row} was not in the expected format")
        output_values_dict_list.append(output_values_dict)
        return output_values_dict_list
