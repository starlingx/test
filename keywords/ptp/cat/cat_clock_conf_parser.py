from framework.exceptions.keyword_exception import KeywordException


class CatClockConfParser:
    """
    Class for cat clock conf parsing

    Example:
        ifname [enp138s0f0]
        base_port [enp138s0f0]
        sma1 input
        ifname [enp81s0f2]
        base_port [enp81s0f0]
        sma1 output
    """

    def __init__(self, cat_clock_conf_output: list[str]):
        """
        Constructor

        Args:
            cat_clock_conf_output (list[str]): a list of strings representing the output of a 'cat clock-conf.conf' command.
        """
        self.cat_clock_conf_output = cat_clock_conf_output

    def get_output_values_dict_list(self) -> list[dict]:
        """
        Getter for output values dict list

        Returns:
            list[dict]: the output values dict list

        """
        output_values_dict_list = []
        output_values_dict = {}
        is_first_ifname = True
        for row in self.cat_clock_conf_output:
            if "~$" in row or "Password:" in row:
                continue  # these prompts and should be ignored
            values = row.strip("\n").split(None, 1)  # split once
            if len(values) == 2:
                key, value = values
                if key.strip() == "ifname" and not is_first_ifname:  # we are now entering a new interface
                    output_values_dict_list.append(output_values_dict)
                    output_values_dict = {}
                elif key.strip() == "ifname" and is_first_ifname:  # this is the first interface
                    is_first_ifname = False
                output_values_dict[key.strip()] = value.strip("[]")
            else:
                raise KeywordException(f"Line with values: {row} was not in the expected format")
        output_values_dict_list.append(output_values_dict)
        return output_values_dict_list
