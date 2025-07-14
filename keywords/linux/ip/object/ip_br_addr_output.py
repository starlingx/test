from keywords.linux.ip.ip_br_addr_parser import IPBrAddrParser
from keywords.linux.ip.object.ip_br_addr_object import IPBrAddrObject
from keywords.linux.ip.object.ip_object import IPObject


class IPBrAddrOutput:
    """
    Class responsible for structuring the output of the 'ip -br addr' command as a list of IPBrAddrObject instances.
    """

    def __init__(self, ip_br_addr_output: str):
        """
        Constructor

        Args:
            ip_br_addr_output (str): a string representing the output of the command 'ip -br addr'.
        """
        self.ip_br_addr_objects: list[IPBrAddrObject] = []
        ip_br_addr_parser = IPBrAddrParser(ip_br_addr_output)
        output_values = ip_br_addr_parser.get_output_values_list()

        for value in output_values:
            ip_br_addr_object = IPBrAddrObject()
            ip_br_addr_object.set_network_interface_name(value.get("network_interface_name"))
            ip_br_addr_object.set_network_interface_status(value.get("network_interface_status"))

            # The column 'ip_addresses' of the output of the command 'ip -br addr' can have zero or many IP addresses.
            if value.get("ip_addresses") is not None:
                for ip in value["ip_addresses"]:
                    ip_object = IPObject(ip)
                    ip_br_addr_object.get_ip_objects().append(ip_object)

            self.ip_br_addr_objects.append(ip_br_addr_object)

    def get_ip_br_addr_objects(self) -> list[IPBrAddrObject]:
        """
        Getter for the list of instances of IPBrAddrObject. Each item of this list is an object the represents a row in the table shown by the execution of the command 'ip -br addr'.

        Returns:
            list[IPBrAddrObject]: list of instances of IPBrAddrObject where each item represents a row in
            the table shown by the execution of the command 'ip -br addr'.
        """
        return self.ip_br_addr_objects
