"""Router object representation."""


class RouterObject:
    """Represents a single OpenStack router.

    Mirrors the parser-then-typed-object pattern used elsewhere under
    ``keywords/openstack/resources/`` (FlavorObject, NetworkObject, etc.).
    """

    def __init__(self) -> None:
        """Initialize an empty RouterObject."""
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

    def get_id(self) -> str:
        """Get the router ID.

        Returns:
            str: Router ID, or empty string if unset.
        """
        return self._properties.get("id", "")

    def set_id(self, router_id: str) -> None:
        """Set the router ID.

        Args:
            router_id (str): Router UUID.
        """
        self._properties["id"] = router_id

    def get_name(self) -> str:
        """Get the router name.

        Returns:
            str: Router name, or empty string if unset.
        """
        return self._properties.get("name", "")

    def set_name(self, name: str) -> None:
        """Set the router name.

        Args:
            name (str): Router name.
        """
        self._properties["name"] = name

    def get_status(self) -> str:
        """Get the router operational status.

        Returns:
            str: Router status, or empty string if unset.
        """
        return self._properties.get("status", "")

    def set_status(self, status: str) -> None:
        """Set the router operational status.

        Args:
            status (str): Router status string.
        """
        self._properties["status"] = status

    def is_admin_state_up(self) -> bool:
        """Get the admin_state_up flag.

        Returns:
            bool: True if admin_state_up is true (the default).
        """
        return bool(self._properties.get("is_admin_state_up", True))

    def set_admin_state_up(self, value: bool) -> None:
        """Set the admin_state_up flag.

        Args:
            value (bool): True if admin_state_up.
        """
        self._properties["is_admin_state_up"] = bool(value)

    def __object_to_string__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"RouterObject(name={self.get_name()}, id={self.get_id()}, status={self.get_status()})"
