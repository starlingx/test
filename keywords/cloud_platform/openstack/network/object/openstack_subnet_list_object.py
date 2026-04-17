"""OpenStack subnet list data object."""


class OpenStackSubnetListObject:
    """Object to represent a single row of the 'openstack subnet list' command."""

    def __init__(self):
        """Initialize OpenStackSubnetListObject."""
        self.id = None
        self.name = None
        self.network = None
        self.subnet = None

    def set_id(self, id: str):
        """Set the subnet id.

        Args:
            id (str): Subnet id.
        """
        self.id = id

    def get_id(self) -> str:
        """Get the subnet id.

        Returns:
            str: Subnet id.
        """
        return self.id

    def set_name(self, name: str):
        """Set the subnet name.

        Args:
            name (str): Subnet name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get the subnet name.

        Returns:
            str: Subnet name.
        """
        return self.name

    def set_network(self, network: str):
        """Set the network id that this subnet belongs to.

        Args:
            network (str): Network id.
        """
        self.network = network

    def get_network(self) -> str:
        """Get the network id that this subnet belongs to.

        Returns:
            str: Network id.
        """
        return self.network

    def set_subnet(self, subnet: str):
        """Set the subnet CIDR.

        Args:
            subnet (str): Subnet CIDR (e.g. '192.168.1.0/24').
        """
        self.subnet = subnet

    def get_subnet(self) -> str:
        """Get the subnet CIDR.

        Returns:
            str: Subnet CIDR (e.g. '192.168.1.0/24').
        """
        return self.subnet

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Human-readable subnet list summary.
        """
        return f"Subnet(id={self.id}, name={self.name}, " f"network={self.network}, subnet={self.subnet})"
