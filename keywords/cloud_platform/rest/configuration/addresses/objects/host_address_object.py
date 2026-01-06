class HostAddressObject:
    """This class represents a Host Address as an object."""

    def __init__(self):
        """Initialize a new HostAddressObject with default values."""
        self.uuid = None
        self.interface_uuid = None
        self.ifname = None
        self.address = None
        self.prefix = -1
        self.enable_dad = False
        self.forihostid = -1
        self.pool_uuid = None

    def set_uuid(self, uuid: str):
        """Set the UUID of the host address.

        Args:
            uuid (str): The unique identifier for the host address.
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """Get the UUID of the host address.

        Returns:
            str: The unique identifier for the host address.
        """
        return self.uuid

    def set_interface_uuid(self, interface_uuid: str):
        """Set the interface UUID associated with this address.

        Args:
            interface_uuid (str): The unique identifier of the network interface.
        """
        self.interface_uuid = interface_uuid

    def get_interface_uuid(self) -> str:
        """Get the interface UUID associated with this address.

        Returns:
            str: The unique identifier of the network interface.
        """
        return self.interface_uuid

    def set_ifname(self, ifname: str):
        """Set the interface name.

        Args:
            ifname (str): The name of the network interface (e.g., 'eth0', 'oam0').
        """
        self.ifname = ifname

    def get_ifname(self) -> str:
        """Get the interface name.

        Returns:
            str: The name of the network interface.
        """
        return self.ifname

    def set_address(self, address: str):
        """Set the IP address.

        Args:
            address (str): The IP address (IPv4 or IPv6).
        """
        self.address = address

    def get_address(self) -> str:
        """Get the IP address.

        Returns:
            str: The IP address (IPv4 or IPv6).
        """
        return self.address

    def set_prefix(self, prefix: int):
        """Set the network prefix length.

        Args:
            prefix (int): The subnet prefix length (e.g., 24 for /24).
        """
        self.prefix = prefix

    def get_prefix(self) -> int:
        """Get the network prefix length.

        Returns:
            int: The subnet prefix length.
        """
        return self.prefix

    def set_enable_dad(self, enable_dad: bool):
        """Set the Duplicate Address Detection (DAD) flag.

        Args:
            enable_dad (bool): Whether DAD is enabled for this address.
        """
        self.enable_dad = enable_dad

    def get_enable_dad(self) -> bool:
        """Get the Duplicate Address Detection (DAD) flag.

        Returns:
            bool: Whether DAD is enabled for this address.
        """
        return self.enable_dad

    def set_forihostid(self, forihostid: int):
        """Set the foreign host ID.

        Args:
            forihostid (int): The ID of the host this address belongs to.
        """
        self.forihostid = forihostid

    def get_forihostid(self) -> int:
        """Get the foreign host ID.

        Returns:
            int: The ID of the host this address belongs to.
        """
        return self.forihostid

    def set_pool_uuid(self, pool_uuid: str):
        """Set the address pool UUID.

        Args:
            pool_uuid (str): The unique identifier of the address pool.
        """
        self.pool_uuid = pool_uuid

    def get_pool_uuid(self) -> str:
        """Get the address pool UUID.

        Returns:
            str: The unique identifier of the address pool.
        """
        return self.pool_uuid
