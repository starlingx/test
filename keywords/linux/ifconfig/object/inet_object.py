class Inet:
    """
    This class represents an Inet (IPv4) attributes as an object.
    """

    def __init__(self):
        """
        Constructor

        Args: None.

        """
        self.inet: str = None
        self.netmask: str = None
        self.broadcast: str = None

    def set_inet(self, inet: str) -> None:
        """
        Sets the inet (IPv4 address).
        """
        self.inet = inet

    def get_inet(self) -> str:
        """
        Gets the inet (IPv4 address).
        """
        return self.inet

    def set_netmask(self, netmask: str) -> None:
        """
        Sets the netmask (subnet mask).
        """
        self.netmask = netmask

    def get_netmask(self) -> str:
        """
        Gets the netmask (subnet mask).
        """
        return self.netmask

    def set_broadcast(self, broadcast: str) -> None:
        """
        Sets the broadcast address.
        """
        self.broadcast = broadcast

    def get_broadcast(self) -> str:
        """
        Gets the broadcast address.
        """
        return self.broadcast
