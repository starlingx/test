"""OpenStack network list data object."""


class OpenStackNetworkListObject:
    """Object to represent a single row of the 'openstack network list' command."""

    def __init__(self):
        """Initialize OpenStackNetworkListObject."""
        self.id = None
        self.name = None
        self.subnets = None

    def set_id(self, id: str):
        """Set the network id.

        Args:
            id (str): Network id.
        """
        self.id = id

    def get_id(self) -> str:
        """Get the network id.

        Returns:
            str: Network id.
        """
        return self.id

    def set_name(self, name: str):
        """Set the network name.

        Args:
            name (str): Network name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get the network name.

        Returns:
            str: Network name.
        """
        return self.name

    def set_subnets(self, subnets: str):
        """Set the subnets string.

        Args:
            subnets (str): Comma-separated subnet UUIDs.
        """
        self.subnets = subnets

    def get_subnets(self) -> str:
        """Get the subnets string.

        Returns:
            str: Comma-separated subnet UUIDs.
        """
        return self.subnets

    def get_subnet_ids(self) -> list[str]:
        """Get the subnet UUIDs as a list.

        Returns:
            list[str]: List of subnet UUIDs. Empty list if no subnets.
        """
        if not self.subnets or self.subnets.strip() == "":
            return []
        return [s.strip() for s in self.subnets.split(",")]

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Human-readable network list summary.
        """
        return f"Network(id={self.id}, name={self.name}, " f"subnets={self.subnets})"
