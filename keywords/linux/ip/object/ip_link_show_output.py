import re

from keywords.linux.ip.object.interface_object import InterfaceObject


class IPLinkShowOutput:
    """
    Class for IP link show
    """

    def __init__(self, ip_link_show_ouput: str):
        self.interface_object: InterfaceObject = None
        self.ip_link_show_output = ip_link_show_ouput

    def get_interface(self) -> InterfaceObject:
        """
        Getter for interface

        Returns:
            InterfaceObject: Parsed interface data.
        """
        # Regex is designed for an output of the shape:
        # 2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP mode DEFAULT group default qlen 1000
        # This regex will extract the interface name, mode, mtu and state

        regex = r"\d+:\s+(?P<interface_name>\S+):\s+<(?P<mode>\S+)>" r"\s+mtu\s+(?P<mtu>\d+)[\s\S]+state\s+(?P<state>\w+)"

        match = re.match(regex, self.ip_link_show_output[0])
        if match:
            interface_name = match.group("interface_name")
            modes = match.group("mode")
            mtu = match.group("mtu")
            state = match.group("state")
            modes,
            self.interface_object = InterfaceObject(interface_name, mtu, state, modes)

        return self.interface_object
