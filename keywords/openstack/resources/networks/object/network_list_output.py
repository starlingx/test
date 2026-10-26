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
            network.set_provider_physical_network(raw.get("provider_physical_network", raw.get("provider:physical_network")))
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

    def discover_bindable_internal_network(self, bindable_physnets: List[str]) -> Optional[NetworkObject]:
        """Discover the first non-external network a VM port can bind on.

        A network is bindable when it has no provider physnet (tenant overlay,
        e.g. VXLAN - always bindable) or its provider physnet is in the OVS
        agent bridge_mappings. Networks on a provider physnet with no bridge
        mapping are skipped because every VM port on them fails to bind
        (PortBindingFailed -> instance ERROR).

        Args:
            bindable_physnets (List[str]): Physnets the OVS agent can bind on
                (the physnets present in the OVS agent bridge_mappings), as
                resolved by the caller.

        Returns:
            Optional[NetworkObject]: First bindable internal network, or None
            if no internal network qualifies.
        """
        for network in self._networks:
            if network.is_router_external():
                continue
            physnet = network.get_provider_physical_network()
            if not physnet or physnet in bindable_physnets:
                get_logger().log_info(f"Discovered bindable internal network: {network.get_name()} ({network.get_id()}), physnet='{physnet or 'none'}'")
                return network
            get_logger().log_info(f"Skipping internal network '{network.get_name()}' on unbindable physnet '{physnet}'")
        get_logger().log_warning(f"No bindable internal network found (bindable physnets: {bindable_physnets})")
        return None

    def __object_to_string__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"NetworkListOutput(count={len(self._networks)})"
