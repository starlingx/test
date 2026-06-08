"""Port object representation."""

from typing import List, Optional


class PortObject:
    """Represents a single OpenStack Neutron port.

    Mirrors the parser-then-typed-object pattern used elsewhere under
    ``keywords/openstack/resources/``. Tests should consume this object
    instead of raw SDK dicts.
    """

    def __init__(self) -> None:
        """Initialize an empty PortObject."""
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
        """Get the port ID.

        Returns:
            str: Port ID, or empty string if unset.
        """
        return self._properties.get("id", "")

    def set_id(self, port_id: str) -> None:
        """Set the port ID.

        Args:
            port_id (str): Port UUID.
        """
        self._properties["id"] = port_id

    def get_name(self) -> str:
        """Get the port name.

        Returns:
            str: Port name, or empty string if unset.
        """
        return self._properties.get("name", "")

    def set_name(self, name: str) -> None:
        """Set the port name.

        Args:
            name (str): Port name.
        """
        self._properties["name"] = name

    def get_status(self) -> str:
        """Get the port operational status (ACTIVE / DOWN / BUILD / ERROR).

        Returns:
            str: Port status, or empty string if unset.
        """
        return self._properties.get("status", "")

    def set_status(self, status: str) -> None:
        """Set the port operational status.

        Args:
            status (str): Port status string.
        """
        self._properties["status"] = status

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

    def get_device_id(self) -> str:
        """Get the device_id (typically the bound server's UUID).

        Returns:
            str: device_id, or empty string if the port is unbound.
        """
        return self._properties.get("device_id", "") or ""

    def set_device_id(self, device_id: str) -> None:
        """Set the device_id.

        Args:
            device_id (str): Bound device UUID.
        """
        self._properties["device_id"] = device_id or ""

    def get_fixed_ips(self) -> List[dict]:
        """Get the list of fixed_ips.

        Returns:
            List[dict]: Fixed-IP allocations (each with 'ip_address' / 'subnet_id').
        """
        return list(self._properties.get("fixed_ips", []) or [])

    def set_fixed_ips(self, fixed_ips: List[dict]) -> None:
        """Set the fixed_ips list.

        Args:
            fixed_ips (List[dict]): Fixed-IP allocations.
        """
        self._properties["fixed_ips"] = list(fixed_ips or [])

    def get_security_group_ids(self) -> List[str]:
        """Get the list of security group IDs attached to the port.

        Returns:
            List[str]: Security-group UUIDs.
        """
        return list(self._properties.get("security_group_ids", []) or [])

    def set_security_group_ids(self, security_group_ids: List[str]) -> None:
        """Set the security group IDs.

        Args:
            security_group_ids (List[str]): Security-group UUIDs.
        """
        self._properties["security_group_ids"] = list(security_group_ids or [])

    def is_port_security_enabled(self) -> Optional[bool]:
        """Get the port_security_enabled flag.

        Returns:
            Optional[bool]: True/False if known, None if the deployment does
            not advertise the attribute.
        """
        return self._properties.get("is_port_security_enabled")

    def set_port_security_enabled(self, value: Optional[bool]) -> None:
        """Set the port_security_enabled flag.

        Args:
            value (Optional[bool]): True/False/None.
        """
        self._properties["is_port_security_enabled"] = value

    def get_dns_name(self) -> str:
        """Get the requested DNS name.

        Returns:
            str: DNS name, or empty string if unset.
        """
        return self._properties.get("dns_name", "") or ""

    def set_dns_name(self, dns_name: str) -> None:
        """Set the DNS name.

        Args:
            dns_name (str): DNS name.
        """
        self._properties["dns_name"] = dns_name or ""

    def get_dns_assignment(self) -> List[dict]:
        """Get the dns_assignment list (FQDNs assigned to the port).

        Returns:
            List[dict]: Each entry has 'hostname', 'ip_address', 'fqdn'.
        """
        return list(self._properties.get("dns_assignment", []) or [])

    def set_dns_assignment(self, dns_assignment: List[dict]) -> None:
        """Set the dns_assignment list.

        Args:
            dns_assignment (List[dict]): DNS assignment entries.
        """
        self._properties["dns_assignment"] = list(dns_assignment or [])

    def __object_to_string__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"PortObject(name={self.get_name()}, id={self.get_id()}, " f"status={self.get_status()}, network_id={self.get_network_id()}, " f"device_id={self.get_device_id()})"
