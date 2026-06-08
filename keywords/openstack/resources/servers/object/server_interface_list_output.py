"""Server-interface list output parsing and access."""

from typing import Dict, List, Optional

from keywords.openstack.resources.servers.object.server_interface_object import ServerInterfaceObject


class ServerInterfaceListOutput:
    """Parses and provides access to a collection of ServerInterfaceObjects."""

    def __init__(self, raw_interfaces: List[Dict]) -> None:
        """Initialize ServerInterfaceListOutput from raw interface dicts.

        Args:
            raw_interfaces (List[Dict]): Raw interface dicts from the
                openstacksdk Compute resource (server_interfaces / attach).
        """
        self._interfaces: List[ServerInterfaceObject] = []
        for raw in raw_interfaces:
            iface = ServerInterfaceObject()
            iface.set_port_id(raw.get("port_id") or raw.get("id") or "")
            iface.set_network_id(raw.get("net_id") or raw.get("network_id") or "")
            for key in ("port_state", "fixed_ips", "mac_addr", "mac_address"):
                if key in raw:
                    iface.set_property(key, raw.get(key))
            self._interfaces.append(iface)

    def get_interfaces(self) -> List[ServerInterfaceObject]:
        """Get all parsed interface objects.

        Returns:
            List[ServerInterfaceObject]: All interfaces in this output.
        """
        return self._interfaces

    def get_interface_by_port_id(self, port_id: str) -> Optional[ServerInterfaceObject]:
        """Get an interface by port ID.

        Args:
            port_id (str): Port UUID.

        Returns:
            Optional[ServerInterfaceObject]: Matching interface, or None.
        """
        for iface in self._interfaces:
            if iface.get_port_id() == port_id:
                return iface
        return None

    def get_count(self) -> int:
        """Get the number of interfaces.

        Returns:
            int: Number of interfaces.
        """
        return len(self._interfaces)

    def __object_to_string__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"ServerInterfaceListOutput(count={len(self._interfaces)})"
