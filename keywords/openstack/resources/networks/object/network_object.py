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
        self.id = ""
        self.name = ""
        self.status = ""
        self.is_external = False
        self.port_security_enabled: Optional[bool] = None
        self.dns_domain = ""
        self.provider_physical_network: Optional[str] = None

    def get_id(self) -> str:
        """Get the network ID.

        Returns:
            str: Network ID, or empty string if unset.
        """
        return self.id

    def set_id(self, network_id: str) -> None:
        """Set the network ID.

        Args:
            network_id (str): Network UUID.
        """
        self.id = network_id

    def get_name(self) -> str:
        """Get the network name.

        Returns:
            str: Network name, or empty string if unset.
        """
        return self.name

    def set_name(self, name: str) -> None:
        """Set the network name.

        Args:
            name (str): Network name.
        """
        self.name = name

    def get_status(self) -> str:
        """Get the network operational status (ACTIVE / DOWN / BUILD / ERROR).

        Returns:
            str: Network status, or empty string if unset.
        """
        return self.status

    def set_status(self, status: str) -> None:
        """Set the network operational status.

        Args:
            status (str): Network status string.
        """
        self.status = status

    def is_router_external(self) -> bool:
        """Check whether this network is the provider/external network.

        Returns:
            bool: True if the network is router:external.
        """
        return self.is_external

    def set_router_external(self, value: bool) -> None:
        """Set the router-external flag.

        Args:
            value (bool): True if the network is router:external.
        """
        self.is_external = bool(value)

    def is_port_security_enabled(self) -> Optional[bool]:
        """Get the port_security_enabled flag for the network.

        Returns:
            Optional[bool]: True/False if known, None if the deployment does
            not advertise the attribute.
        """
        return self.port_security_enabled

    def set_port_security_enabled(self, value: Optional[bool]) -> None:
        """Set the port_security_enabled flag.

        Args:
            value (Optional[bool]): True/False/None.
        """
        self.port_security_enabled = value

    def get_dns_domain(self) -> str:
        """Get the configured dns_domain (Neutron 'dns' ml2 extension).

        Returns:
            str: DNS domain string, or empty string if unset.
        """
        return self.dns_domain

    def set_dns_domain(self, dns_domain: str) -> None:
        """Set the dns_domain attribute.

        Args:
            dns_domain (str): DNS domain string.
        """
        self.dns_domain = dns_domain

    def get_provider_physical_network(self) -> str:
        """Get the provider:physical_network of the network.

        Returns:
            str: Provider physnet name, or empty string if the network has no
            provider physnet (e.g. a tenant VXLAN network).
        """
        return self.provider_physical_network or ""

    def set_provider_physical_network(self, provider_physical_network: Optional[str]) -> None:
        """Set the provider:physical_network attribute.

        Args:
            provider_physical_network (Optional[str]): Provider physnet name.
        """
        self.provider_physical_network = provider_physical_network

    def __object_to_string__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"NetworkObject(name={self.get_name()}, id={self.get_id()}, " f"status={self.get_status()}, router_external={self.is_router_external()})"
