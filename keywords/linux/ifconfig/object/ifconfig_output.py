import re

from keywords.linux.ifconfig.object.ifconfig_object import IfConfigObject
from keywords.linux.ifconfig.object.inet6_object import Inet6
from keywords.linux.ifconfig.object.inet_object import Inet


class IfConfigOutput:
    """
    This class parses the output of 'ifconfig -a' commands into a list of IfConfigObjects.
    Note: Netrom interfaces are not considered.
    """

    def __init__(self, ifconfig_output: str):
        """
        Constructor

        Args:
            ifconfig_output: String output of 'ifconfig -a' command

        """
        self.ifconfig_objects: list[IfConfigObject] = []

        """
        The output of the 'ifconfig' command shows some items like that:

        apxeboot: flags=5187<UP,BROADCAST,RUNNING,MASTER,MULTICAST> mtu 1500
        inet 200.224.202.2  netmask 255.255.255.0  broadcast 200.224.202.255
        inet6 ffff::dddd:feff:fea1:3228  prefixlen 64  scopeid 0x20<link>
        ether 5c:fd:fe:a1:32:28  txqueuelen 1000  (Ethernet)
        RX packets 649707801  bytes 456281185903 (424.9 GiB)
        RX errors 0  dropped 115121  overruns 0  frame 0
        TX packets 528230099  bytes 254949626663 (237.4 GiB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

        In the example above, this class will extract data from the first four lines of this 'ifconfig item'. The
        regular expressions below are designed to extract the attributes of each associated line.
        """

        # Regular expression for the interface section of an ifconfig item, e.g.,
        #   'apxeboot: flags=5187<UP,BROADCAST,RUNNING,MASTER,MULTICAST>  mtu 1500'
        # This regular expression is designed to extract:
        # 1. the interface name, e.g., 'apxeboot';
        # 2. the flags, e.g., '5187<UP,BROADCAST,RUNNING,MASTER,MULTICAST>';
        # 3. the mtu (Maximum Transmission Unit), e.g., 1500.
        interface_pattern = re.compile(r'^(?P<interface_name>[^\s:]+):\s*flags=(?P<flags>[0-9a-fA-F]+(?:<[^>]*>)?)\s+mtu\s+(?P<mtu>\d+)$')

        # Regular expression for the inet section of an ifconfig item, e.g.,
        #   'inet 200.224.202.2  netmask 255.255.255.0  broadcast 200.224.202.255'
        # This regular expression is designed to extract:
        # 1. the IPv4 address (inet), e.g., '200.224.202.2';
        # 2. the netmask, e.g., '255.255.255.0';
        # 3. the broadcast address, e.g., '200.224.202.255'.
        inet_pattern = re.compile(r"\s*inet\s+(?P<inet>\d{1,3}(?:\.\d{1,3}){3})\s+netmask\s+(?P<netmask>\d{1,3}(?:\.\d{1,3}){3})\s+broadcast\s+(?P<broadcast>\d{1,3}(?:\.\d{1,3}){3})\s*")

        # Regular expression for the inet6 section of an ifconfig item, e.g.,
        #   'inet6 ffff::dddd:feff:fea1:3228  prefixlen 64  scopeid 0x20<link>'
        # This regular expression is designed to extract:
        # 1. the IPv6 address (inet6), e.g., 'ffff::dddd:feff:fea1:3228';
        # 2. the prefixlen, e.g., '64';
        # 3. the scopeid, e.g., '0x20<link>'
        inet6_pattern = re.compile(r'inet6\s+(?P<inet6>[0-9a-fA-F:]+)\s+prefixlen\s+(?P<prefixlen>\d+)\s+scopeid\s+(?P<scopeid>0x[0-9a-fA-F]+(?:<[^>]+>)?)')

        # Regular expression for the ether section of an ifconfig item, e.g.,
        #   'ether 5c:fd:fe:a1:32:28  txqueuelen 1000  (Ethernet)'
        # This regular expression is designed to extract:
        # 1. the MAC address, e.g., '5c:fd:fe:a1:32:28';
        # 2. the txqueuelen, e.g., '1000'.
        ether_pattern = re.compile(r'^\s*ether\s+(?P<ether>[0-9a-fA-F:]{17})\s+txqueuelen\s+(?P<txqueuelen>\d+)')

        ifconfig_object: IfConfigObject = None
        for item in ifconfig_output:
            interface_match = interface_pattern.match(item)
            # If the name of an interface is matched, create a new object IfConfigObject.
            if interface_match:
                ifconfig_object = IfConfigObject()
                ifconfig_object.interface_name = interface_match.group('interface_name')
                ifconfig_object.flags = interface_match.group('flags')
                ifconfig_object.mtu = interface_match.group('mtu')
                continue

            if ifconfig_object is None:
                continue

            # Extract the IPv6 data.
            inet6_match = inet6_pattern.search(item)
            if inet6_match:
                inet6_object: Inet6 = Inet6()
                inet6_object.set_inet6(inet6_match.group('inet6'))
                inet6_object.set_prefix_len(inet6_match.group('prefixlen'))
                inet6_object.set_scope_id(inet6_match.group('scopeid'))
                ifconfig_object.get_inet6_objects().append(inet6_object)
                continue

            # Extract the IPv4 data.
            inet_match = inet_pattern.match(item)
            if inet_match:
                inet_object: Inet = Inet()
                inet_object.set_inet(inet_match.group('inet'))
                inet_object.set_netmask(inet_match.group('netmask'))
                inet_object.set_broadcast(inet_match.group('broadcast'))
                ifconfig_object.get_inet_objects().append(inet_object)
                continue

            # Extract the Ethernet data.
            ether_match = ether_pattern.match(item)
            if ether_match:
                ifconfig_object.ether = ether_match.group('ether')
                ifconfig_object.txqueuelen = ether_match.group('txqueuelen')
                if ifconfig_object is not None:
                    self.ifconfig_objects.append(ifconfig_object)

    def get_ifconfig_objects(self):
        return self.ifconfig_objects
