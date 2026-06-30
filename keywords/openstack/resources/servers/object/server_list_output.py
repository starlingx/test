"""Output parser for Nova server SDK responses."""

from typing import List

from keywords.openstack.resources.servers.object.server_object import ServerObject


class ServerListOutput:
    """Parses OpenStack SDK server dicts into ServerObject instances."""

    def __init__(self, raw_servers: List[dict]):
        """Initialize and parse server dicts.

        Args:
            raw_servers (List[dict]): List of server dicts from SDK to_dict().
        """
        self._servers: List[ServerObject] = []
        for raw in raw_servers:
            server = ServerObject()
            server.set_id(raw.get("id", ""))
            server.set_name(raw.get("name", ""))
            server.set_status(raw.get("status", ""))
            server.set_host(
                raw.get("OS-EXT-SRV-ATTR:host")
                or raw.get("host")
                or raw.get("compute_host", "")
            )
            server.set_availability_zone(
                raw.get("OS-EXT-AZ:availability_zone")
                or raw.get("availability_zone", "")
            )
            flavor = raw.get("flavor", {})
            server.set_flavor_id(flavor.get("id", "") if isinstance(flavor, dict) else "")
            image = raw.get("image", {})
            server.set_image_id(image.get("id", "") if isinstance(image, dict) else "")
            server.set_addresses(raw.get("addresses", {}))
            server.set_created_at(raw.get("created_at") or raw.get("created", ""))
            server.set_updated_at(raw.get("updated_at") or raw.get("updated", ""))
            server.set_tenant_id(raw.get("tenant_id") or raw.get("project_id", ""))
            server.set_user_id(raw.get("user_id", ""))
            server.set_key_name(raw.get("key_name", ""))
            server.set_metadata(raw.get("metadata", {}))
            self._servers.append(server)

    def get_servers(self) -> List[ServerObject]:
        """Get the list of parsed servers.

        Returns:
            List[ServerObject]: List of server objects.
        """
        return self._servers

    def get_server_by_name(self, name: str) -> ServerObject:
        """Get a server by name.

        Args:
            name (str): Server name.

        Returns:
            ServerObject: Matching server.

        Raises:
            KeyError: If no server with that name is found.
        """
        for server in self._servers:
            if server.get_name() == name:
                return server
        raise KeyError(f"Server '{name}' not found")

    def get_server_by_id(self, server_id: str) -> ServerObject:
        """Get a server by ID.

        Args:
            server_id (str): Server ID.

        Returns:
            ServerObject: Matching server.

        Raises:
            KeyError: If no server with that ID is found.
        """
        for server in self._servers:
            if server.get_id() == server_id:
                return server
        raise KeyError(f"Server with ID '{server_id}' not found")
