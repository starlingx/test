from keywords.ptp.cat.cat_ptp_table_parser import CatPtpTableParser
from keywords.ptp.cat.objects.transport_options_object import TransportOptionsObject


class TransportOptionsOutput:
    """
    This class parses the output of Transport Options

    Example:
        transportSpecific       0x0
        ptp_dst_mac             01:1B:19:00:00:00
        p2p_dst_mac             01:80:C2:00:00:0E
        udp_ttl                 1
        udp6_scope              0x0E
        uds_address             /var/run/ptp4l
        uds_ro_address          /var/run/ptp4lro

    """

    def __init__(self, transport_options_output: [str]):
        """
        Constructor.
            Create an internal ServoOptionsObject from the passed parameter.
        Args:
            transport_options_output (list[str]): a list of strings representing the servo options output

        """
        cat_ptp_table_parser = CatPtpTableParser(transport_options_output)
        output_values = cat_ptp_table_parser.get_output_values_dict()
        self.transport_options_object = TransportOptionsObject()

        if 'transportSpecific' in output_values:
            self.transport_options_object.set_transport_specific(output_values['transportSpecific'])

        if 'ptp_dst_mac' in output_values:
            self.transport_options_object.set_ptp_dst_mac(output_values['ptp_dst_mac'])

        if 'p2p_dst_mac' in output_values:
            self.transport_options_object.set_p2p_dst_mac(output_values['p2p_dst_mac'])

        if 'udp_ttl' in output_values:
            self.transport_options_object.set_udp_ttl(int(output_values['udp_ttl']))

        if 'udp6_scope' in output_values:
            self.transport_options_object.set_udp6_scope(output_values['udp6_scope'])

        if 'uds_address' in output_values:
            self.transport_options_object.set_uds_address(output_values['uds_address'])

        if 'uds_ro_address' in output_values:
            self.transport_options_object.set_uds_ro_address(output_values['uds_ro_address'])

    def get_transport_options_object(self) -> TransportOptionsObject:
        """
        Getter for TransportOptionsObject object.

        Returns:
            A TransportOptionsObject

        """
        return self.transport_options_object
