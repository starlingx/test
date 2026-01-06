from keywords.ptp.cat.cat_ptp_table_parser import CatPtpTableParser
from keywords.ptp.cat.objects.default_interface_options_object import DefaultInterfaceOptionsObject


class DefaultInterfaceOptionsOutput:
    """
    This class parses the output of Default Interface Options

    Example:
        clock_type              OC
        network_transport       UDPv4
        delay_mechanism         E2E
        time_stamping           hardware
        tsproc_mode             filter
        delay_filter            moving_median
        delay_filter_length     10
        egressLatency           0
        ingressLatency          0
        boundary_clock_jbod     0

    """

    def __init__(self, default_interface_options_output: list[str]):
        """
        Create an internal DefaultInterfaceOptionsObject from the passed parameter.

        Args:
            default_interface_options_output (list[str]): a list of strings representing the default interface options output
        """
        cat_ptp_table_parser = CatPtpTableParser(default_interface_options_output)
        output_values = cat_ptp_table_parser.get_output_values_dict()
        self.default_interface_options_object = DefaultInterfaceOptionsObject()

        if "clock_type" in output_values:
            self.default_interface_options_object.set_clock_type(output_values["clock_type"])

        if "network_transport" in output_values:
            self.default_interface_options_object.set_network_transport(output_values["network_transport"])

        if "delay_mechanism" in output_values:
            self.default_interface_options_object.set_delay_mechanism(output_values["delay_mechanism"])

        if "time_stamping" in output_values:
            self.default_interface_options_object.set_time_stamping(output_values["time_stamping"])

        if "tsproc_mode" in output_values:
            self.default_interface_options_object.set_tsproc_mode(output_values["tsproc_mode"])

        if "delay_filter" in output_values:
            self.default_interface_options_object.set_delay_filter(output_values["delay_filter"])

        if "delay_filter_length" in output_values:
            self.default_interface_options_object.set_delay_filter_length(int(output_values["delay_filter_length"]))

        if "egressLatency" in output_values:
            self.default_interface_options_object.set_egress_latency(int(output_values["egressLatency"]))

        if "ingressLatency" in output_values:
            self.default_interface_options_object.set_ingress_latency(int(output_values["ingressLatency"]))

        if "boundary_clock_jbod" in output_values:
            self.default_interface_options_object.set_boundary_clock_jbod(int(output_values["boundary_clock_jbod"]))

    def get_default_interface_options_object(self) -> DefaultInterfaceOptionsObject:
        """
        Getter for DefaultInterfaceOptionsObject object.

        Returns:
            DefaultInterfaceOptionsObject: The default interface options object containing parsed values.
        """
        return self.default_interface_options_object
