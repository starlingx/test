"""OpenStack port list data object."""


class OpenStackPortListObject:
    """Object to represent a single port from the 'openstack port list' command."""

    def __init__(self):
        """Initialize OpenStackPortListObject."""
        self.id = None
        self.name = None
        self.mac_address = None
        self.fixed_ip_addresses = None
        self.status = None

    def set_id(self, port_id: str):
        """Set the port id.

        Args:
            port_id (str): Port id.
        """
        self.id = port_id

    def get_id(self) -> str:
        """Get the port id.

        Returns:
            str: Port id.
        """
        return self.id

    def set_name(self, name: str):
        """Set the port name.

        Args:
            name (str): Port name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get the port name.

        Returns:
            str: Port name.
        """
        return self.name

    def set_mac_address(self, mac_address: str):
        """Set the MAC address.

        Args:
            mac_address (str): MAC address.
        """
        self.mac_address = mac_address

    def get_mac_address(self) -> str:
        """Get the MAC address.

        Returns:
            str: MAC address.
        """
        return self.mac_address

    def set_fixed_ip_addresses(self, fixed_ip_addresses: str):
        """Set the fixed IP addresses string.

        Args:
            fixed_ip_addresses (str): Fixed IP addresses as returned by CLI.
        """
        self.fixed_ip_addresses = fixed_ip_addresses

    def get_fixed_ip_addresses(self) -> str:
        """Get the fixed IP addresses string.

        Returns:
            str: Fixed IP addresses as returned by CLI.
        """
        return self.fixed_ip_addresses

    def append_fixed_ip_addresses(self, extra: str):
        """Append additional fixed IP addresses from a continuation line.

        Args:
            extra (str): Additional fixed IP addresses text to append.
        """
        if self.fixed_ip_addresses:
            self.fixed_ip_addresses = f"{self.fixed_ip_addresses} {extra}"
        else:
            self.fixed_ip_addresses = extra

    def set_status(self, status: str):
        """Set the port status.

        Args:
            status (str): Port status (e.g. ACTIVE, DOWN, BUILD).
        """
        self.status = status

    def get_status(self) -> str:
        """Get the port status.

        Returns:
            str: Port status.
        """
        return self.status

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Human-readable port summary.
        """
        return f"Port(id={self.id}, name={self.name}, " f"mac={self.mac_address}, " f"fixed_ips={self.fixed_ip_addresses}, " f"status={self.status})"
