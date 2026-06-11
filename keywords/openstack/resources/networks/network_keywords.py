"""Network, subnet, router, and port CRUD keywords via OpenStack SDK.

All methods follow the parser-then-typed-object pattern used elsewhere
under ``keywords/openstack/resources/`` (see flavors/, images/, keypairs/):
SDK responses are passed through a ``*ListOutput`` parser which produces
typed ``*Object`` wrappers. Tests get a stable surface that's resilient
to upstream SDK shape changes.
"""

from typing import Optional

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from keywords.openstack.resources.networks.object.network_list_output import NetworkListOutput
from keywords.openstack.resources.networks.object.network_object import NetworkObject
from keywords.openstack.resources.networks.object.port_list_output import PortListOutput
from keywords.openstack.resources.networks.object.port_object import PortObject
from keywords.openstack.resources.networks.object.router_list_output import RouterListOutput
from keywords.openstack.resources.networks.object.router_object import RouterObject
from keywords.openstack.resources.networks.object.subnet_list_output import SubnetListOutput
from keywords.openstack.resources.networks.object.subnet_object import SubnetObject


class NetworkKeywords(BaseKeyword):
    """CRUD operations for Neutron resources via OpenStack SDK."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize NetworkKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    # ── Network CRUD ────────────────────────────────────────────────

    def create_network(
        self,
        network_name: str,
        port_security_enabled: Optional[bool] = None,
        dns_domain: Optional[str] = None,
    ) -> NetworkObject:
        """Create a network.

        Args:
            network_name (str): Network name.
            port_security_enabled (Optional[bool]): If set, force port_security_enabled
                at network create time. Defaults to deployment-wide setting.
            dns_domain (Optional[str]): DNS domain to attach to the network for
                internal DNS (requires the 'dns' ml2 extension).

        Returns:
            NetworkObject: Parsed network object.
        """
        get_logger().log_info(f"Creating network '{network_name}'")
        network = self.openstack_connection.get_network().create_network(
            name=network_name,
            port_security_enabled=port_security_enabled,
            dns_domain=dns_domain,
        )
        return NetworkListOutput([network.to_dict()]).get_networks()[0]

    def show_network(self, network_name_or_id: str) -> NetworkObject:
        """Show network details.

        Args:
            network_name_or_id (str): Network name or ID.

        Returns:
            NetworkObject: Parsed network object.
        """
        network = self.openstack_connection.get_network().find_network(network_name_or_id, ignore_missing=False)
        return NetworkListOutput([network.to_dict()]).get_networks()[0]

    def list_networks(self) -> NetworkListOutput:
        """List all networks.

        Returns:
            NetworkListOutput: Parsed network collection.
        """
        raw = [n.to_dict() for n in self.openstack_connection.get_network().networks()]
        return NetworkListOutput(raw)

    def update_network(
        self,
        network_name_or_id: str,
        new_name: Optional[str] = None,
        port_security_enabled: Optional[bool] = None,
    ) -> NetworkObject:
        """Update a network's name or port-security setting.

        Args:
            network_name_or_id (str): Network name or ID.
            new_name (Optional[str]): New network name.
            port_security_enabled (Optional[bool]): If set, toggle port_security_enabled.

        Returns:
            NetworkObject: Parsed updated network object.
        """
        net_service = self.openstack_connection.get_network()
        network = net_service.find_network(network_name_or_id, ignore_missing=False)
        attrs = {}
        if new_name:
            attrs["name"] = new_name
        if port_security_enabled is not None:
            attrs["port_security_enabled"] = port_security_enabled
        updated = net_service.update_network(network.id, **attrs)
        return NetworkListOutput([updated.to_dict()]).get_networks()[0]

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

    def create_subnet(
        self,
        subnet_name: str,
        network_name_or_id: str,
        subnet_range: str,
        ip_version: int = 4,
        gateway_ip: Optional[str] = None,
        no_gateway: bool = False,
        ipv6_ra_mode: Optional[str] = None,
        ipv6_address_mode: Optional[str] = None,
    ) -> SubnetObject:
        """Create a subnet on a network.

        Args:
            subnet_name (str): Subnet name.
            network_name_or_id (str): Parent network name or ID.
            subnet_range (str): CIDR range (e.g. '192.168.100.0/24' or 'fd00::/64').
            ip_version (int): IP version, 4 or 6. Defaults to 4.
            gateway_ip (Optional[str]): Explicit gateway IP. If None, Neutron picks one.
            no_gateway (bool): If True, create the subnet without a gateway address.
            ipv6_ra_mode (Optional[str]): IPv6 router advertisement mode (e.g. 'dhcpv6-stateful').
            ipv6_address_mode (Optional[str]): IPv6 address mode (e.g. 'dhcpv6-stateful').

        Returns:
            SubnetObject: Parsed subnet object.
        """
        get_logger().log_info(f"Creating subnet '{subnet_name}' on network '{network_name_or_id}' " f"({subnet_range}, ipv{ip_version})")
        net_service = self.openstack_connection.get_network()
        network = net_service.find_network(network_name_or_id, ignore_missing=False)
        attrs = {
            "name": subnet_name,
            "network_id": network.id,
            "cidr": subnet_range,
            "ip_version": ip_version,
        }
        if no_gateway:
            attrs["gateway_ip"] = None
        elif gateway_ip is not None:
            attrs["gateway_ip"] = gateway_ip
        if ipv6_ra_mode is not None:
            attrs["ipv6_ra_mode"] = ipv6_ra_mode
        if ipv6_address_mode is not None:
            attrs["ipv6_address_mode"] = ipv6_address_mode
        subnet = net_service.create_subnet(**attrs)
        return SubnetListOutput([subnet.to_dict()]).get_subnets()[0]

    def show_subnet(self, subnet_name_or_id: str) -> SubnetObject:
        """Show subnet details.

        Args:
            subnet_name_or_id (str): Subnet name or ID.

        Returns:
            SubnetObject: Parsed subnet object.
        """
        subnet = self.openstack_connection.get_network().find_subnet(subnet_name_or_id, ignore_missing=False)
        return SubnetListOutput([subnet.to_dict()]).get_subnets()[0]

    def list_subnets(self) -> SubnetListOutput:
        """List all subnets.

        Returns:
            SubnetListOutput: Parsed subnet collection.
        """
        raw = [s.to_dict() for s in self.openstack_connection.get_network().subnets()]
        return SubnetListOutput(raw)

    def update_subnet(
        self,
        subnet_name_or_id: str,
        new_name: Optional[str] = None,
        no_dhcp: bool = False,
    ) -> SubnetObject:
        """Update a subnet.

        Args:
            subnet_name_or_id (str): Subnet name or ID.
            new_name (Optional[str]): New subnet name.
            no_dhcp (bool): Disable DHCP if True.

        Returns:
            SubnetObject: Parsed updated subnet object.
        """
        net_service = self.openstack_connection.get_network()
        subnet = net_service.find_subnet(subnet_name_or_id, ignore_missing=False)
        attrs = {}
        if new_name:
            attrs["name"] = new_name
        if no_dhcp:
            attrs["is_dhcp_enabled"] = False
        updated = net_service.update_subnet(subnet.id, **attrs)
        return SubnetListOutput([updated.to_dict()]).get_subnets()[0]

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

    def create_router(self, router_name: str) -> RouterObject:
        """Create a router.

        Args:
            router_name (str): Router name.

        Returns:
            RouterObject: Parsed router object.
        """
        get_logger().log_info(f"Creating router '{router_name}'")
        router = self.openstack_connection.get_network().create_router(name=router_name)
        return RouterListOutput([router.to_dict()]).get_routers()[0]

    def show_router(self, router_name_or_id: str) -> RouterObject:
        """Show router details.

        Args:
            router_name_or_id (str): Router name or ID.

        Returns:
            RouterObject: Parsed router object.
        """
        router = self.openstack_connection.get_network().find_router(router_name_or_id, ignore_missing=False)
        return RouterListOutput([router.to_dict()]).get_routers()[0]

    def list_routers(self) -> RouterListOutput:
        """List all routers.

        Returns:
            RouterListOutput: Parsed router collection.
        """
        raw = [r.to_dict() for r in self.openstack_connection.get_network().routers()]
        return RouterListOutput(raw)

    def update_router(
        self,
        router_name_or_id: str,
        new_name: Optional[str] = None,
    ) -> RouterObject:
        """Update a router's name.

        Args:
            router_name_or_id (str): Router name or ID.
            new_name (Optional[str]): New router name.

        Returns:
            RouterObject: Parsed updated router object.
        """
        net_service = self.openstack_connection.get_network()
        router = net_service.find_router(router_name_or_id, ignore_missing=False)
        attrs = {}
        if new_name:
            attrs["name"] = new_name
        updated = net_service.update_router(router.id, **attrs)
        return RouterListOutput([updated.to_dict()]).get_routers()[0]

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

    def create_port(
        self,
        port_name: str,
        network_name_or_id: str,
        port_security_enabled: Optional[bool] = None,
        security_groups: Optional[list] = None,
        dns_name: Optional[str] = None,
    ) -> PortObject:
        """Create a port on a network.

        Args:
            port_name (str): Port name.
            network_name_or_id (str): Network name or ID.
            port_security_enabled (Optional[bool]): Override port_security_enabled
                at port create time.
            security_groups (Optional[list]): Security group IDs to assign.
                Use [] together with port_security_enabled=False to create an
                unsecured port.
            dns_name (Optional[str]): DNS name for the port (requires the 'dns'
                ml2 extension and a network with dns_domain set).

        Returns:
            PortObject: Parsed port object.
        """
        get_logger().log_info(f"Creating port '{port_name}' on network '{network_name_or_id}'")
        net_service = self.openstack_connection.get_network()
        network = net_service.find_network(network_name_or_id, ignore_missing=False)
        attrs = {"name": port_name, "network_id": network.id}
        if port_security_enabled is not None:
            attrs["port_security_enabled"] = port_security_enabled
        if security_groups is not None:
            attrs["security_group_ids"] = security_groups
        if dns_name is not None:
            attrs["dns_name"] = dns_name
        port = net_service.create_port(**attrs)
        return PortListOutput([port.to_dict()]).get_ports()[0]

    def show_port(self, port_name_or_id: str) -> PortObject:
        """Show port details.

        Args:
            port_name_or_id (str): Port name or ID.

        Returns:
            PortObject: Parsed port object.
        """
        port = self.openstack_connection.get_network().find_port(port_name_or_id, ignore_missing=False)
        return PortListOutput([port.to_dict()]).get_ports()[0]

    def list_ports(self) -> PortListOutput:
        """List all ports.

        Returns:
            PortListOutput: Parsed port collection.
        """
        raw = [p.to_dict() for p in self.openstack_connection.get_network().ports()]
        return PortListOutput(raw)

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

    def discover_internal_network(self) -> NetworkObject:
        """Discover the first available internal (non-external) network.

        Returns:
            NetworkObject: Parsed network object.

        Raises:
            RuntimeError: If no networks are found.
        """
        return self.list_networks().discover_internal_network()

    def discover_external_network(self) -> Optional[NetworkObject]:
        """Discover the first available external network.

        Returns:
            Optional[NetworkObject]: Parsed network object, or None if no
            external network exists.
        """
        return self.list_networks().discover_external_network()

    # ── Cleanup helpers ─────────────────────────────────────────────

    def cleanup_network(self, network_name_or_id: str) -> None:
        """Safely delete a network if it exists. Does not raise on failure.

        Args:
            network_name_or_id (str): Network name or ID.
        """
        net_service = self.openstack_connection.get_network()
        network = net_service.find_network(network_name_or_id, ignore_missing=True)
        if network is None:
            get_logger().log_info(f"Network '{network_name_or_id}' already gone, skipping cleanup")
            return
        try:
            net_service.delete_network(network.id)
            get_logger().log_info(f"Cleaned up network: {network_name_or_id}")
        except Exception as e:
            get_logger().log_warning(f"Network cleanup failed for '{network_name_or_id}': {e}")

    def cleanup_subnet(self, subnet_name_or_id: str) -> None:
        """Safely delete a subnet if it exists. Does not raise on failure.

        Args:
            subnet_name_or_id (str): Subnet name or ID.
        """
        net_service = self.openstack_connection.get_network()
        subnet = net_service.find_subnet(subnet_name_or_id, ignore_missing=True)
        if subnet is None:
            get_logger().log_info(f"Subnet '{subnet_name_or_id}' already gone, skipping cleanup")
            return
        try:
            net_service.delete_subnet(subnet.id)
            get_logger().log_info(f"Cleaned up subnet: {subnet_name_or_id}")
        except Exception as e:
            get_logger().log_warning(f"Subnet cleanup failed for '{subnet_name_or_id}': {e}")

    def cleanup_port(self, port_name_or_id: str) -> None:
        """Safely delete a port if it exists. Does not raise on failure.

        Args:
            port_name_or_id (str): Port name or ID.
        """
        net_service = self.openstack_connection.get_network()
        port = net_service.find_port(port_name_or_id, ignore_missing=True)
        if port is None:
            get_logger().log_info(f"Port '{port_name_or_id}' already gone, skipping cleanup")
            return
        try:
            net_service.delete_port(port.id)
            get_logger().log_info(f"Cleaned up port: {port_name_or_id}")
        except Exception as e:
            get_logger().log_warning(f"Port cleanup failed for '{port_name_or_id}': {e}")

    # ── Negative-test helpers ───────────────────────────────────────

    def create_subnet_expect_error(
        self,
        subnet_name: str,
        network_name_or_id: str,
        subnet_range: str,
        ip_version: int = 4,
        gateway_ip: Optional[str] = None,
    ) -> str:
        """Attempt to create a subnet and return the error message.

        Used for negative testing where the subnet creation is expected to
        fail (e.g., overlapping CIDR, invalid gateway IP).

        Args:
            subnet_name (str): Subnet name.
            network_name_or_id (str): Parent network name or ID.
            subnet_range (str): CIDR range.
            ip_version (int): IP version, 4 or 6.
            gateway_ip (Optional[str]): Explicit (possibly invalid) gateway IP.

        Returns:
            str: Error message from the failed subnet attempt.

        Raises:
            AssertionError: If subnet creation unexpectedly succeeds.
        """
        get_logger().log_info(f"Attempting subnet '{subnet_name}' on '{network_name_or_id}' (expecting failure)")
        try:
            subnet = self.create_subnet(
                subnet_name=subnet_name,
                network_name_or_id=network_name_or_id,
                subnet_range=subnet_range,
                ip_version=ip_version,
                gateway_ip=gateway_ip,
            )
            self.cleanup_subnet(subnet.get_id())
            raise AssertionError(f"Subnet '{subnet_name}' was created unexpectedly — expected an error")
        except AssertionError:
            raise
        except Exception as e:
            error_message = str(e)
            get_logger().log_info(f"Subnet correctly rejected: {error_message}")
            return error_message
