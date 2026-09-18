"""Typed object for a single OpenStack Neutron floating IP."""


class FloatingIpObject:
    """Represents a single OpenStack Neutron floating IP.

    Mirrors the parser-then-typed-object pattern used elsewhere under
    ``keywords/openstack/resources/``. Callers should consume this object
    instead of reaching into raw SDK floating-IP resources.
    """

    def __init__(self) -> None:
        """Initialize an empty FloatingIpObject."""
        self._properties: dict = {}

    def set_property(self, key: str, value: object) -> None:
        """Set a property value.

        Args:
            key (str): Property name.
            value (object): Property value.
        """
        self._properties[key] = value

    def get_property(self, key: str) -> object:
        """Get a property value.

        Args:
            key (str): Property name.

        Returns:
            object: Property value, or None if not set.
        """
        return self._properties.get(key)

    def get_id(self) -> str:
        """Get the floating IP ID.

        Returns:
            str: Floating IP UUID, or empty string if unset.
        """
        return self._properties.get("id", "")

    def set_id(self, floating_ip_id: str) -> None:
        """Set the floating IP ID.

        Args:
            floating_ip_id (str): Floating IP UUID.
        """
        self._properties["id"] = floating_ip_id

    def get_floating_ip_address(self) -> str:
        """Get the floating IP address.

        Returns:
            str: Floating IP address (e.g. '10.10.98.5'), or empty string if unset.
        """
        return self._properties.get("floating_ip_address", "")

    def set_floating_ip_address(self, floating_ip_address: str) -> None:
        """Set the floating IP address.

        Args:
            floating_ip_address (str): Floating IP address.
        """
        self._properties["floating_ip_address"] = floating_ip_address

    def get_status(self) -> str:
        """Get the floating IP status (ACTIVE / DOWN).

        Returns:
            str: Floating IP status, or empty string if unset.
        """
        return self._properties.get("status", "")

    def set_status(self, status: str) -> None:
        """Set the floating IP status.

        Args:
            status (str): Floating IP status string.
        """
        self._properties["status"] = status

    def get_port_id(self) -> str:
        """Get the ID of the port this floating IP is associated with.

        Returns:
            str: Bound port UUID, or empty string if the floating IP is not
            associated with a port.
        """
        return self._properties.get("port_id", "") or ""

    def set_port_id(self, port_id: str) -> None:
        """Set the associated port ID.

        Args:
            port_id (str): Bound port UUID (empty string when unassociated).
        """
        self._properties["port_id"] = port_id or ""

    def get_floating_network_id(self) -> str:
        """Get the external network ID the floating IP was allocated from.

        Returns:
            str: External network UUID, or empty string if unset.
        """
        return self._properties.get("floating_network_id", "")

    def set_floating_network_id(self, floating_network_id: str) -> None:
        """Set the external network ID the floating IP was allocated from.

        Args:
            floating_network_id (str): External network UUID.
        """
        self._properties["floating_network_id"] = floating_network_id

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"FloatingIpObject(id={self.get_id()}, address={self.get_floating_ip_address()}, port_id={self.get_port_id()}, status={self.get_status()})"
