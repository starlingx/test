"""Subnet list output parsing and access."""

from typing import Dict, List

from keywords.openstack.resources.networks.object.subnet_object import SubnetObject


class SubnetListOutput:
    """Parses and provides access to a collection of SubnetObjects.

    Same pattern as FlavorListOutput / NetworkListOutput: takes raw
    openstacksdk dicts and produces typed wrapper objects.
    """

    def __init__(self, raw_subnets: List[Dict]) -> None:
        """Initialize SubnetListOutput from raw subnet dicts.

        Args:
            raw_subnets (List[Dict]): Raw subnet dicts from the
                openstacksdk Network resource.
        """
        self._subnets: List[SubnetObject] = []
        for raw in raw_subnets:
            subnet = SubnetObject()
            subnet.set_id(raw.get("id", ""))
            subnet.set_name(raw.get("name", ""))
            subnet.set_network_id(raw.get("network_id", ""))
            subnet.set_cidr(raw.get("cidr", ""))
            subnet.set_ip_version(raw.get("ip_version", 0) or 0)
            subnet.set_gateway_ip(raw.get("gateway_ip"))
            subnet.set_ipv6_ra_mode(raw.get("ipv6_ra_mode"))
            subnet.set_ipv6_address_mode(raw.get("ipv6_address_mode"))
            subnet.set_dhcp_enabled(raw.get("is_dhcp_enabled", raw.get("enable_dhcp", True)))
            subnet.set_allocation_pools(raw.get("allocation_pools") or [])
            self._subnets.append(subnet)

    def get_subnets(self) -> List[SubnetObject]:
        """Get all parsed subnet objects.

        Returns:
            List[SubnetObject]: All subnets in this output.
        """
        return self._subnets

    def get_subnet_by_name(self, name: str) -> SubnetObject:
        """Get a subnet by name.

        Args:
            name (str): Subnet name.

        Returns:
            SubnetObject: Matching subnet.

        Raises:
            ValueError: If no subnet with the given name is found.
        """
        for subnet in self._subnets:
            if subnet.get_name() == name:
                return subnet
        raise ValueError(f"Subnet '{name}' not found")

    def is_subnet_present(self, name: str) -> bool:
        """Check whether a subnet with the given name exists in this output.

        Args:
            name (str): Subnet name.

        Returns:
            bool: True if a matching subnet is present.
        """
        for subnet in self._subnets:
            if subnet.get_name() == name:
                return True
        return False

    def __object_to_string__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"SubnetListOutput(count={len(self._subnets)})"
