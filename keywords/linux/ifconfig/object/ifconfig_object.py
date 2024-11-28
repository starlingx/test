from keywords.linux.ifconfig.object.inet6_object import Inet6
from keywords.linux.ifconfig.object.inet_object import Inet


class IfConfigObject:
    """
    This class represents an item of the output of 'ifconfig command' as an object.
    """

    def __init__(self):
        """
        Constructor

        Args: None.

        """
        self.interface_name: str = None
        self.flags: str = None
        self.mtu: int = -1
        self.inet6_objects: list['Inet6'] = []
        self.inet_objects: list['Inet'] = []
        self.ether: str = None
        self.tx_queue_len: int = -1

    def set_interface_name(self, interface_name: str) -> None:
        """
        Sets the interface name.
        """
        self.interface_name = interface_name

    def get_interface_name(self) -> str:
        """
        Gets the interface name.
        """
        return self.interface_name

    def set_flags(self, flags: str) -> None:
        """
        Sets the flags.
        """
        self.flags = flags

    def get_flags(self) -> str:
        """
        Gets the flags.
        """
        return self.flags

    def set_mtu(self, mtu: int) -> None:
        """
        Sets the MTU (Maximum Transmission Unit).
        """
        self.mtu = mtu

    def get_mtu(self) -> int:
        """
        Gets the MTU.
        """
        return self.mtu

    def set_inet6_objects(self, inet6_objects: list['Inet6']) -> None:
        """
        Sets the inet6 objects.
        """
        self.inet6_objects = inet6_objects

    def get_inet6_objects(self) -> list['Inet6']:
        """
        Gets the inet6 objects.
        """
        return self.inet6_objects

    def set_inet_objects(self, inet_objects: list['Inet']) -> None:
        """
        Sets the inet objects.
        """
        self.inet_objects = inet_objects

    def get_inet_objects(self) -> list['Inet']:
        """
        Gets the inet objects.
        """
        return self.inet_objects

    def set_ether(self, ether: str) -> None:
        """
        Sets the ether (MAC address).
        """
        self.ether = ether

    def get_ether(self) -> str:
        """
        Gets the ether (MAC address).
        """
        return self.ether

    def set_tx_queue_len(self, tx_queue_len: int) -> None:
        """
        Sets the transmission queue length.
        """
        self.tx_queue_len = tx_queue_len

    def get_tx_queue_len(self) -> int:
        """
        Gets the transmission queue length.
        """
        return self.tx_queue_len
