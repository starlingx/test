"""Port list output parsing and access."""

from typing import Dict, List, Optional

from keywords.openstack.resources.networks.object.port_object import PortObject


class PortListOutput:
    """Parses and provides access to a collection of PortObjects."""

    def __init__(self, raw_ports: List[Dict]) -> None:
        """Initialize PortListOutput from raw port dicts.

        Args:
            raw_ports (List[Dict]): Raw port dicts from the openstacksdk
                Network resource.
        """
        self._ports: List[PortObject] = []
        for raw in raw_ports:
            port = PortObject()
            port.set_id(raw.get("id", ""))
            port.set_name(raw.get("name", ""))
            port.set_status(raw.get("status", ""))
            port.set_network_id(raw.get("network_id", ""))
            port.set_device_id(raw.get("device_id", "") or "")
            port.set_fixed_ips(raw.get("fixed_ips") or [])
            port.set_security_group_ids(raw.get("security_group_ids", raw.get("security_groups")) or [])
            port.set_port_security_enabled(raw.get("is_port_security_enabled", raw.get("port_security_enabled")))
            port.set_dns_name(raw.get("dns_name", "") or "")
            port.set_dns_assignment(raw.get("dns_assignment") or [])
            self._ports.append(port)

    def get_ports(self) -> List[PortObject]:
        """Get all parsed port objects.

        Returns:
            List[PortObject]: All ports in this output.
        """
        return self._ports

    def get_port_by_name(self, name: str) -> PortObject:
        """Get a port by name.

        Args:
            name (str): Port name.

        Returns:
            PortObject: Matching port.

        Raises:
            ValueError: If no port with the given name is found.
        """
        for port in self._ports:
            if port.get_name() == name:
                return port
        raise ValueError(f"Port '{name}' not found")

    def get_ports_by_device_id(self, device_id: str) -> List[PortObject]:
        """Filter ports by device_id (e.g. server UUID).

        Args:
            device_id (str): The device UUID.

        Returns:
            List[PortObject]: All ports bound to the given device.
        """
        return [port for port in self._ports if port.get_device_id() == device_id]

    def get_port_by_id(self, port_id: str) -> Optional[PortObject]:
        """Get a port by ID.

        Args:
            port_id (str): Port UUID.

        Returns:
            Optional[PortObject]: Matching port or None.
        """
        for port in self._ports:
            if port.get_id() == port_id:
                return port
        return None

    def is_port_present(self, name: str) -> bool:
        """Check whether a port with the given name exists in this output.

        Args:
            name (str): Port name.

        Returns:
            bool: True if a matching port is present.
        """
        for port in self._ports:
            if port.get_name() == name:
                return True
        return False

    def __object_to_string__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"PortListOutput(count={len(self._ports)})"
