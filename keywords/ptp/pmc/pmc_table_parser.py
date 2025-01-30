import re

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

    def __init__(self, pmc_output):
        """
        Constructor
        Args:
            pmc_output (list[str]): a list of strings representing the output of a 'pmc' command.
        """
        self.pmc_output = pmc_output

    def get_output_values_dict(
            self,
    ):
        """
        Getter for output values dict
        Returns: the output values dict

        """

        output_values_dict = {}

        total_rows = len(self.pmc_output)

        for row in self.pmc_output[2:total_rows - 1]:  # Ignore the first 2 rows and the last row (prompt)
            values = row.split(None, 1)  # split once
            if len(values) == 2:
                key, value = values
                output_values_dict[key.strip()] = value.strip()
            else:
                raise KeywordException(f"Line with values: {row} was not in the expected format")
        return output_values_dict
