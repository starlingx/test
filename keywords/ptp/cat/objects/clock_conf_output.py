from keywords.ptp.cat.cat_clock_conf_parser import CatClockConfParser
from keywords.ptp.cat.objects.clock_conf_object import ClockConfObject


class ClockConfOutput:
    """
    This class parses the output of cat clock conf file

    Example:
        ifname [enp138s0f0]
        base_port [enp138s0f0]
        sma1 input
        ifname [enp81s0f0]
        base_port [enp81s0f0]
        sma1 output


    """

    def __init__(self, clock_conf_output: list[str]):
        """
        Constructor.

            Create an internal ClockConfObject from the passed parameter.

        Args:
            clock_conf_output (list[str]): a list of strings representing the clock conf output

        """
        cat_clock_conf_parser = CatClockConfParser(clock_conf_output)
        output_values = cat_clock_conf_parser.get_output_values_dict_list()
        self.clock_conf_objects: list[ClockConfObject] = []

        for values in output_values:
            clock_conf_object = ClockConfObject()

            if "ifname" in values:
                clock_conf_object.set_ifname(values["ifname"])

            if "base_port" in values:
                clock_conf_object.set_base_port(values["base_port"])

            if "sma1" in values:
                clock_conf_object.set_sma_name("sma1")
                clock_conf_object.set_sma_mode(values["sma1"])

            if "sma2" in values:
                clock_conf_object.set_sma_name("sma2")
                clock_conf_object.set_sma_mode(values["sma2"])
            self.clock_conf_objects.append(clock_conf_object)

    def get_clock_conf_objects(self) -> list[ClockConfObject]:
        """
        Getter for ClockConfObject objects.

        Returns:
            list[ClockConfObject]: A list ClockDescriptionObjects

        """
        return self.clock_conf_objects
