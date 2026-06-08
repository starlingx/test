"""Subnet object representation."""

from typing import List, Optional


class SubnetObject:
    """Represents a single OpenStack subnet.

    Mirrors the parser-then-typed-object pattern used elsewhere under
    ``keywords/openstack/resources/`` (FlavorObject, NetworkObject, etc.):
    keyword methods return wrappers like this instead of raw SDK dicts so
    tests get a stable, type-safe surface even if the upstream SDK shape
    changes.
    """

    def __init__(self) -> None:
        """Initialize an empty SubnetObject."""
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
        """Get the subnet ID.

        Returns:
            str: Subnet ID, or empty string if unset.
        """
        return self._properties.get("id", "")

    def set_id(self, subnet_id: str) -> None:
        """Set the subnet ID.

        Args:
            subnet_id (str): Subnet UUID.
        """
        self._properties["id"] = subnet_id

    def get_name(self) -> str:
        """Get the subnet name.

        Returns:
            str: Subnet name, or empty string if unset.
        """
        return self._properties.get("name", "")

    def set_name(self, name: str) -> None:
        """Set the subnet name.

        Args:
            name (str): Subnet name.
        """
        self._properties["name"] = name

    def get_network_id(self) -> str:
        """Get the parent network ID.

        Returns:
            str: Parent network UUID, or empty string if unset.
        """
        return self._properties.get("network_id", "")

    def set_network_id(self, network_id: str) -> None:
        """Set the parent network ID.

        Args:
            network_id (str): Parent network UUID.
        """
        self._properties["network_id"] = network_id

    def get_cidr(self) -> str:
        """Get the subnet CIDR.

        Returns:
            str: CIDR string, or empty string if unset.
        """
        return self._properties.get("cidr", "")

    def set_cidr(self, cidr: str) -> None:
        """Set the subnet CIDR.

        Args:
            cidr (str): CIDR string.
        """
        self._properties["cidr"] = cidr

    def get_ip_version(self) -> int:
        """Get the IP version (4 or 6).

        Returns:
            int: IP version, or 0 if unset.
        """
        return int(self._properties.get("ip_version", 0))

    def set_ip_version(self, ip_version: int) -> None:
        """Set the IP version.

        Args:
            ip_version (int): IP version (4 or 6).
        """
        self._properties["ip_version"] = int(ip_version)

    def get_gateway_ip(self) -> Optional[str]:
        """Get the gateway IP.

        Returns:
            Optional[str]: Gateway IP, or None if no gateway is set.
        """
        return self._properties.get("gateway_ip")

    def set_gateway_ip(self, gateway_ip: Optional[str]) -> None:
        """Set the gateway IP.

        Args:
            gateway_ip (Optional[str]): Gateway IP, or None for no-gateway.
        """
        self._properties["gateway_ip"] = gateway_ip

    def get_ipv6_ra_mode(self) -> Optional[str]:
        """Get the IPv6 router-advertisement mode.

        Returns:
            Optional[str]: IPv6 RA mode (e.g. 'slaac'), or None if unset.
        """
        return self._properties.get("ipv6_ra_mode")

    def set_ipv6_ra_mode(self, ipv6_ra_mode: Optional[str]) -> None:
        """Set the IPv6 router-advertisement mode.

        Args:
            ipv6_ra_mode (Optional[str]): IPv6 RA mode.
        """
        self._properties["ipv6_ra_mode"] = ipv6_ra_mode

    def get_ipv6_address_mode(self) -> Optional[str]:
        """Get the IPv6 address mode.

        Returns:
            Optional[str]: IPv6 address mode (e.g. 'slaac'), or None if unset.
        """
        return self._properties.get("ipv6_address_mode")

    def set_ipv6_address_mode(self, ipv6_address_mode: Optional[str]) -> None:
        """Set the IPv6 address mode.

        Args:
            ipv6_address_mode (Optional[str]): IPv6 address mode.
        """
        self._properties["ipv6_address_mode"] = ipv6_address_mode

    def is_dhcp_enabled(self) -> bool:
        """Check whether DHCP is enabled on the subnet.

        Returns:
            bool: True if DHCP is enabled (the SDK default).
        """
        return bool(self._properties.get("is_dhcp_enabled", True))

    def set_dhcp_enabled(self, value: bool) -> None:
        """Set the DHCP-enabled flag.

        Args:
            value (bool): True to enable DHCP.
        """
        self._properties["is_dhcp_enabled"] = bool(value)

    def get_allocation_pools(self) -> List[dict]:
        """Get the list of allocation pools.

        Returns:
            List[dict]: Allocation pools (each with 'start' / 'end').
        """
        return list(self._properties.get("allocation_pools", []) or [])

    def set_allocation_pools(self, pools: List[dict]) -> None:
        """Set the allocation pools.

        Args:
            pools (List[dict]): Allocation pools.
        """
        self._properties["allocation_pools"] = list(pools or [])

    def __object_to_string__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"SubnetObject(name={self.get_name()}, id={self.get_id()}, " f"network_id={self.get_network_id()}, cidr={self.get_cidr()}, " f"ip_version={self.get_ip_version()}, gateway_ip={self.get_gateway_ip()})"
