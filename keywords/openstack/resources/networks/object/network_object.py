"""Network object representation."""

from typing import Optional


class NetworkObject:
    """Represents a single OpenStack network.

    Mirrors the parser-then-typed-object pattern used elsewhere under
    ``keywords/openstack/resources/`` (FlavorObject, KeypairObject, etc.):
    keyword methods return wrappers like this instead of raw SDK dicts so
    tests get a stable, type-safe surface even if the upstream SDK shape
    changes.
    """

    def __init__(self) -> None:
        """Initialize an empty NetworkObject."""
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
        """Get the network ID.

        Returns:
            str: Network ID, or empty string if unset.
        """
        return self._properties.get("id", "")

    def set_id(self, network_id: str) -> None:
        """Set the network ID.

        Args:
            network_id (str): Network UUID.
        """
        self._properties["id"] = network_id

    def get_name(self) -> str:
        """Get the network name.

        Returns:
            str: Network name, or empty string if unset.
        """
        return self._properties.get("name", "")

    def set_name(self, name: str) -> None:
        """Set the network name.

        Args:
            name (str): Network name.
        """
        self._properties["name"] = name

    def get_status(self) -> str:
        """Get the network operational status (ACTIVE / DOWN / BUILD / ERROR).

        Returns:
            str: Network status, or empty string if unset.
        """
        return self._properties.get("status", "")

    def set_status(self, status: str) -> None:
        """Set the network operational status.

        Args:
            status (str): Network status string.
        """
        self._properties["status"] = status

    def is_router_external(self) -> bool:
        """Check whether this network is the provider/external network.

        Returns:
            bool: True if the network is router:external.
        """
        return bool(self._properties.get("is_router_external", False))

    def set_router_external(self, value: bool) -> None:
        """Set the router-external flag.

        Args:
            value (bool): True if the network is router:external.
        """
        self._properties["is_router_external"] = bool(value)

    def is_port_security_enabled(self) -> Optional[bool]:
        """Get the port_security_enabled flag for the network.

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

    def get_dns_domain(self) -> str:
        """Get the configured dns_domain (Neutron 'dns' ml2 extension).

        Returns:
            str: DNS domain string, or empty string if unset.
        """
        return self._properties.get("dns_domain", "")

    def set_dns_domain(self, dns_domain: str) -> None:
        """Set the dns_domain attribute.

        Args:
            dns_domain (str): DNS domain string.
        """
        self._properties["dns_domain"] = dns_domain

    def __object_to_string__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"NetworkObject(name={self.get_name()}, id={self.get_id()}, " f"status={self.get_status()}, router_external={self.is_router_external()})"
