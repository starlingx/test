"""Server interface attachment object representation."""

from typing import List


class ServerInterfaceObject:
    """Represents a single Nova server-interface attachment.

    Wraps the SDK's ServerInterface dict in a typed accessor so tests
    don't have to deal with the dual ``id`` / ``port_id`` and
    ``net_id`` / ``network_id`` keys returned by different SDK versions.
    """

    def __init__(self) -> None:
        """Initialize an empty ServerInterfaceObject."""
        self._properties: dict = {}

    def set_property(self, key: str, value: object) -> None:
        """Set a property value.

        Args:
            key (str): Property name.
            value (object): Property value.
        """
        self._properties[key] = value

    def get_property(self, key: str) -> object:
        """Get a property value.

        Args:
            key (str): Property name.

        Returns:
            object: Property value, or None if not set.
        """
        return self._properties.get(key)

    def get_port_id(self) -> str:
        """Get the port ID.

        The SDK exposes the port via ``port_id`` on attach responses but
        as ``id`` on server_interfaces() listings; this returns whichever
        is available.

        Returns:
            str: Port UUID, or empty string if unset.
        """
        return self._properties.get("port_id") or self._properties.get("id") or ""

    def set_port_id(self, port_id: str) -> None:
        """Set the port ID.

        Args:
            port_id (str): Port UUID.
        """
        self._properties["port_id"] = port_id

    def get_network_id(self) -> str:
        """Get the network ID.

        Returns:
            str: Network UUID, or empty string if unset.
        """
        return self._properties.get("net_id") or self._properties.get("network_id") or ""

    def set_network_id(self, network_id: str) -> None:
        """Set the network ID.

        Args:
            network_id (str): Network UUID.
        """
        self._properties["net_id"] = network_id

    def get_port_state(self) -> str:
        """Get the port state (e.g. ACTIVE, DOWN).

        Returns:
            str: Port state, or empty string if unset.
        """
        return self._properties.get("port_state", "") or ""

    def get_fixed_ips(self) -> List[dict]:
        """Get the list of fixed IPs attached to this interface.

        Returns:
            List[dict]: Fixed-IP allocations.
        """
        return list(self._properties.get("fixed_ips") or [])

    def __object_to_string__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"ServerInterfaceObject(port_id={self.get_port_id()}, " f"network_id={self.get_network_id()}, state={self.get_port_state()})"
