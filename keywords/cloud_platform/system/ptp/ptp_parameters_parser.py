import re
from typing import Union


class PTPParametersParser:
    """
    Class for ptp parameters parsing

    Example:
          ['domainNumber=24', 'dataset_comparison=G.8275.x', 'priority2=110', 'boundary_clock_jbod=1']
          cmdline_opts=-s xxxx -O -37 -m boundary_clock_jbod=1 domainNumber=24
    """

    def __init__(self, parameters: Union[str, list]):
        """
        Constructor

        Args:
            parameters Union[str, list]): The input data, which can be a string
                containing cmdline_opts or a list of strings representing
                ptp parameters.
        """
        self.parameters = parameters

    def process_cmdline_opts(self) -> str:
        """
        Processes the cmdline_opts data, handling both string and list inputs,
        to ensure the value is enclosed in single quotes.

        Returns:
            str: The modified string with the cmdline_opts value properly quoted,
                or the original input string if cmdline_opts is not found.
        """
        if isinstance(self.parameters, list):
            parameters_str = " ".join(self.parameters)  # Convert list to string
        else:
            parameters_str = self.parameters

        match = re.search(r"(cmdline_opts=)(.*?)(?=\s+\w+=|$)", parameters_str)

        if match:
            prefix, value = match.group(1), match.group(2).strip()
            if not (value.startswith("'") and value.endswith("'")):
                value = f"'{value}'"
            output_str = parameters_str.replace(match.group(0), f"{prefix}{value}")
        else:
            output_str = parameters_str

        return output_str
