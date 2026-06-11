"""Network list output parsing and access."""

from typing import Dict, List, Optional

from framework.logging.automation_logger import get_logger
from keywords.openstack.resources.networks.object.network_object import NetworkObject


class NetworkListOutput:
    """Parses and provides access to a collection of NetworkObjects.

    Same pattern as FlavorListOutput / KeypairListOutput: takes raw
    openstacksdk dicts and produces typed wrapper objects.
    """

    def __init__(self, raw_networks: List[Dict]) -> None:
        """Initialize NetworkListOutput from raw network dicts.

        Args:
            raw_networks (List[Dict]): Raw network dicts from the
                openstacksdk Network resource.
        """
        self._networks: List[NetworkObject] = []
        for raw in raw_networks:
            network = NetworkObject()
            network.set_id(raw.get("id", ""))
            network.set_name(raw.get("name", ""))
            network.set_status(raw.get("status", ""))
            network.set_router_external(raw.get("is_router_external", raw.get("router:external", False)))
            network.set_port_security_enabled(raw.get("is_port_security_enabled", raw.get("port_security_enabled")))
            network.set_dns_domain(raw.get("dns_domain", ""))
            self._networks.append(network)

    def get_networks(self) -> List[NetworkObject]:
        """Get all parsed network objects.

        Returns:
            List[NetworkObject]: All networks in this output.
        """
        return self._networks

    def get_network_by_name(self, name: str) -> NetworkObject:
        """Get a network by name.

        Args:
            name (str): Network name.

        Returns:
            NetworkObject: Matching network.

        Raises:
            ValueError: If no network with the given name is found.
        """
        for network in self._networks:
            if network.get_name() == name:
                return network
        raise ValueError(f"Network '{name}' not found")

    def is_network_present(self, name: str) -> bool:
        """Check whether a network with the given name exists in this output.

        Args:
            name (str): Network name.

        Returns:
            bool: True if a matching network is present.
        """
        for network in self._networks:
            if network.get_name() == name:
                return True
        return False

    def discover_internal_network(self) -> NetworkObject:
        """Discover the first non-external (tenant) network.

        Returns:
            NetworkObject: Discovered internal network.

        Raises:
            RuntimeError: If no networks are available at all.
        """
        if not self._networks:
            raise RuntimeError("No networks found in Neutron")
        for network in self._networks:
            if not network.is_router_external():
                get_logger().log_info(f"Discovered internal network: {network.get_name()} ({network.get_id()})")
                return network
        get_logger().log_warning(f"No non-external network found, using: {self._networks[0].get_name()}")
        return self._networks[0]

    def discover_external_network(self) -> Optional[NetworkObject]:
        """Discover the first router:external network.

        Returns:
            Optional[NetworkObject]: External network, or None if none exists.
        """
        for network in self._networks:
            if network.is_router_external():
                get_logger().log_info(f"Discovered external network: {network.get_name()} ({network.get_id()})")
                return network
        get_logger().log_warning("No external network found")
        return None

    def __object_to_string__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"NetworkListOutput(count={len(self._networks)})"
