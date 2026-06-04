"""Network, subnet, router, and port CRUD keywords via OpenStack SDK."""

from typing import Dict, List, Optional

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword

from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection


class NetworkKeywords(BaseKeyword):
    """CRUD operations for Neutron resources via OpenStack SDK."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize NetworkKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    # ── Network CRUD ────────────────────────────────────────────────

    def create_network(self, network_name: str) -> Dict:
        """Create a network.

        Args:
            network_name (str): Network name.

        Returns:
            Dict: Network details.
        """
        get_logger().log_info(f"Creating network '{network_name}'")
        network = self.openstack_connection.get_network().create_network(name=network_name)
        return network.to_dict()

    def show_network(self, network_name_or_id: str) -> Dict:
        """Show network details.

        Args:
            network_name_or_id (str): Network name or ID.

        Returns:
            Dict: Network details.
        """
        network = self.openstack_connection.get_network().find_network(network_name_or_id, ignore_missing=False)
        return network.to_dict()

    def list_networks(self) -> List[Dict]:
        """List all networks.

        Returns:
            List[Dict]: List of network dicts.
        """
        return [n.to_dict() for n in self.openstack_connection.get_network().networks()]

    def update_network(self, network_name_or_id: str, new_name: Optional[str] = None) -> Dict:
        """Update a network's name.

        Args:
            network_name_or_id (str): Network name or ID.
            new_name (Optional[str]): New network name.

        Returns:
            Dict: Updated network details.
        """
        net_service = self.openstack_connection.get_network()
        network = net_service.find_network(network_name_or_id, ignore_missing=False)
        attrs = {}
        if new_name:
            attrs["name"] = new_name
        updated = net_service.update_network(network.id, **attrs)
        return updated.to_dict()

    def delete_network(self, network_name_or_id: str) -> None:
        """Delete a network.

        Args:
            network_name_or_id (str): Network name or ID.
        """
        get_logger().log_info(f"Deleting network '{network_name_or_id}'")
        net_service = self.openstack_connection.get_network()
        network = net_service.find_network(network_name_or_id, ignore_missing=False)
        net_service.delete_network(network.id)

    # ── Subnet CRUD ─────────────────────────────────────────────────

    def create_subnet(self, subnet_name: str, network_name_or_id: str, subnet_range: str) -> Dict:
        """Create a subnet on a network.

        Args:
            subnet_name (str): Subnet name.
            network_name_or_id (str): Parent network name or ID.
            subnet_range (str): CIDR range (e.g. '192.168.100.0/24').

        Returns:
            Dict: Subnet details.
        """
        get_logger().log_info(f"Creating subnet '{subnet_name}' on network '{network_name_or_id}' ({subnet_range})")
        net_service = self.openstack_connection.get_network()
        network = net_service.find_network(network_name_or_id, ignore_missing=False)
        subnet = net_service.create_subnet(
            name=subnet_name,
            network_id=network.id,
            cidr=subnet_range,
            ip_version=4,
        )
        return subnet.to_dict()

    def show_subnet(self, subnet_name_or_id: str) -> Dict:
        """Show subnet details.

        Args:
            subnet_name_or_id (str): Subnet name or ID.

        Returns:
            Dict: Subnet details.
        """
        subnet = self.openstack_connection.get_network().find_subnet(subnet_name_or_id, ignore_missing=False)
        return subnet.to_dict()

    def list_subnets(self) -> List[Dict]:
        """List all subnets.

        Returns:
            List[Dict]: List of subnet dicts.
        """
        return [s.to_dict() for s in self.openstack_connection.get_network().subnets()]

    def update_subnet(self, subnet_name_or_id: str, new_name: Optional[str] = None, no_dhcp: bool = False) -> Dict:
        """Update a subnet.

        Args:
            subnet_name_or_id (str): Subnet name or ID.
            new_name (Optional[str]): New subnet name.
            no_dhcp (bool): Disable DHCP if True.

        Returns:
            Dict: Updated subnet details.
        """
        net_service = self.openstack_connection.get_network()
        subnet = net_service.find_subnet(subnet_name_or_id, ignore_missing=False)
        attrs = {}
        if new_name:
            attrs["name"] = new_name
        if no_dhcp:
            attrs["is_dhcp_enabled"] = False
        updated = net_service.update_subnet(subnet.id, **attrs)
        return updated.to_dict()

    def delete_subnet(self, subnet_name_or_id: str) -> None:
        """Delete a subnet.

        Args:
            subnet_name_or_id (str): Subnet name or ID.
        """
        get_logger().log_info(f"Deleting subnet '{subnet_name_or_id}'")
        net_service = self.openstack_connection.get_network()
        subnet = net_service.find_subnet(subnet_name_or_id, ignore_missing=False)
        net_service.delete_subnet(subnet.id)

    # ── Router CRUD ─────────────────────────────────────────────────

    def create_router(self, router_name: str) -> Dict:
        """Create a router.

        Args:
            router_name (str): Router name.

        Returns:
            Dict: Router details.
        """
        get_logger().log_info(f"Creating router '{router_name}'")
        router = self.openstack_connection.get_network().create_router(name=router_name)
        return router.to_dict()

    def show_router(self, router_name_or_id: str) -> Dict:
        """Show router details.

        Args:
            router_name_or_id (str): Router name or ID.

        Returns:
            Dict: Router details.
        """
        router = self.openstack_connection.get_network().find_router(router_name_or_id, ignore_missing=False)
        return router.to_dict()

    def list_routers(self) -> List[Dict]:
        """List all routers.

        Returns:
            List[Dict]: List of router dicts.
        """
        return [r.to_dict() for r in self.openstack_connection.get_network().routers()]

    def update_router(self, router_name_or_id: str, new_name: Optional[str] = None) -> Dict:
        """Update a router's name.

        Args:
            router_name_or_id (str): Router name or ID.
            new_name (Optional[str]): New router name.

        Returns:
            Dict: Updated router details.
        """
        net_service = self.openstack_connection.get_network()
        router = net_service.find_router(router_name_or_id, ignore_missing=False)
        attrs = {}
        if new_name:
            attrs["name"] = new_name
        updated = net_service.update_router(router.id, **attrs)
        return updated.to_dict()

    def delete_router(self, router_name_or_id: str) -> None:
        """Delete a router.

        Args:
            router_name_or_id (str): Router name or ID.
        """
        get_logger().log_info(f"Deleting router '{router_name_or_id}'")
        net_service = self.openstack_connection.get_network()
        router = net_service.find_router(router_name_or_id, ignore_missing=False)
        net_service.delete_router(router.id)

    def add_subnet_to_router(self, router_name_or_id: str, subnet_name_or_id: str) -> None:
        """Add a subnet interface to a router.

        Args:
            router_name_or_id (str): Router name or ID.
            subnet_name_or_id (str): Subnet name or ID.
        """
        get_logger().log_info(f"Adding subnet '{subnet_name_or_id}' to router '{router_name_or_id}'")
        net_service = self.openstack_connection.get_network()
        router = net_service.find_router(router_name_or_id, ignore_missing=False)
        subnet = net_service.find_subnet(subnet_name_or_id, ignore_missing=False)
        net_service.add_interface_to_router(router.id, subnet_id=subnet.id)

    def remove_subnet_from_router(self, router_name_or_id: str, subnet_name_or_id: str) -> None:
        """Remove a subnet interface from a router.

        Args:
            router_name_or_id (str): Router name or ID.
            subnet_name_or_id (str): Subnet name or ID.
        """
        get_logger().log_info(f"Removing subnet '{subnet_name_or_id}' from router '{router_name_or_id}'")
        net_service = self.openstack_connection.get_network()
        router = net_service.find_router(router_name_or_id, ignore_missing=False)
        subnet = net_service.find_subnet(subnet_name_or_id, ignore_missing=False)
        net_service.remove_interface_from_router(router.id, subnet_id=subnet.id)

    # ── Port CRUD ───────────────────────────────────────────────────

    def create_port(self, port_name: str, network_name_or_id: str) -> Dict:
        """Create a port on a network.

        Args:
            port_name (str): Port name.
            network_name_or_id (str): Network name or ID.

        Returns:
            Dict: Port details.
        """
        get_logger().log_info(f"Creating port '{port_name}' on network '{network_name_or_id}'")
        net_service = self.openstack_connection.get_network()
        network = net_service.find_network(network_name_or_id, ignore_missing=False)
        port = net_service.create_port(name=port_name, network_id=network.id)
        return port.to_dict()

    def show_port(self, port_name_or_id: str) -> Dict:
        """Show port details.

        Args:
            port_name_or_id (str): Port name or ID.

        Returns:
            Dict: Port details.
        """
        port = self.openstack_connection.get_network().find_port(port_name_or_id, ignore_missing=False)
        return port.to_dict()

    def list_ports(self) -> List[Dict]:
        """List all ports.

        Returns:
            List[Dict]: List of port dicts.
        """
        return [p.to_dict() for p in self.openstack_connection.get_network().ports()]

    def delete_port(self, port_name_or_id: str) -> None:
        """Delete a port.

        Args:
            port_name_or_id (str): Port name or ID.
        """
        get_logger().log_info(f"Deleting port '{port_name_or_id}'")
        net_service = self.openstack_connection.get_network()
        port = net_service.find_port(port_name_or_id, ignore_missing=False)
        net_service.delete_port(port.id)

    # ── Discovery ───────────────────────────────────────────────────

    def discover_internal_network(self) -> Dict:
        """Discover the first available internal (non-external) network.

        Returns:
            Dict: Network details.

        Raises:
            RuntimeError: If no networks are found.
        """
        networks = list(self.openstack_connection.get_network().networks())
        if not networks:
            raise RuntimeError("No networks found in Neutron")

        for n in networks:
            if not n.is_router_external:
                get_logger().log_info(f"Discovered internal network: {n.name} ({n.id})")
                return n.to_dict()

        get_logger().log_warning(f"No non-external network found, using: {networks[0].name}")
        return networks[0].to_dict()

    def discover_external_network(self) -> Optional[Dict]:
        """Discover the first available external network.

        Returns:
            Optional[Dict]: Network details, or None if no external network exists.
        """
        for n in self.openstack_connection.get_network().networks():
            if n.is_router_external:
                get_logger().log_info(f"Discovered external network: {n.name} ({n.id})")
                return n.to_dict()

        get_logger().log_warning("No external network found")
        return None
