"""Server list output parsing and access."""

from typing import Dict, List, Optional

from keywords.openstack.resources.servers.object.server_object import ServerObject


class ServerListOutput:
    """Parses and provides access to a collection of ServerObjects."""

    def __init__(self, raw_servers: List[Dict]) -> None:
        """Initialize ServerListOutput from raw server dicts.

        Args:
            raw_servers (List[Dict]): Raw server dicts from the openstacksdk
                Compute resource.
        """
        self._servers: List[ServerObject] = []
        for raw in raw_servers:
            server = ServerObject()
            server.set_id(raw.get("id", ""))
            server.set_name(raw.get("name", ""))
            server.set_status(raw.get("status", ""))
            server.set_image(raw.get("image"))
            server.set_flavor(raw.get("flavor"))
            server.set_metadata(raw.get("metadata") or {})
            server.set_addresses(raw.get("addresses") or {})
            server.set_fault(raw.get("fault"))
            # Pass-through extras the convenience getters need
            for key in (
                "availability_zone",
                "compute_host",
                "hypervisor_hostname",
                "OS-EXT-SRV-ATTR:host",
                "security_groups",
            ):
                if key in raw:
                    server.set_property(key, raw.get(key))
            self._servers.append(server)

    def get_servers(self) -> List[ServerObject]:
        """Get all parsed server objects.

        Returns:
            List[ServerObject]: All servers in this output.
        """
        return self._servers

    def get_server_by_name(self, name: str) -> ServerObject:
        """Get a server by name.

        Args:
            name (str): Server name.

        Returns:
            ServerObject: Matching server.

        Raises:
            ValueError: If no server with the given name is found.
        """
        for server in self._servers:
            if server.get_name() == name:
                return server
        raise ValueError(f"Server '{name}' not found")

    def get_server_by_id(self, server_id: str) -> Optional[ServerObject]:
        """Get a server by ID.

        Args:
            server_id (str): Server UUID.

        Returns:
            Optional[ServerObject]: Matching server, or None.
        """
        for server in self._servers:
            if server.get_id() == server_id:
                return server
        return None

    def is_server_present(self, name: str) -> bool:
        """Check whether a server with the given name exists in this output.

        Args:
            name (str): Server name.

        Returns:
            bool: True if a matching server is present.
        """
        for server in self._servers:
            if server.get_name() == name:
                return True
        return False

    def __object_to_string__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"ServerListOutput(count={len(self._servers)})"
