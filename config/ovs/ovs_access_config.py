"""Typed OVSAccess test configuration."""


class OvsAccessConfig:
    """Typed OVSAccess test configuration.

    Accessed via OvsConfig.get_ovsaccess_config().
    """

    def __init__(self, ovsaccess_dict: dict):
        """Initialize from the ovsaccess dictionary.

        Args:
            ovsaccess_dict: Dict with keys interface_name, node_name.
        """
        self._data = ovsaccess_dict

    def get_interface_name(self) -> str:
        """Get the SR-IOV interface name for OVSAccess."""
        return self._data["interface_name"]

    def get_node_name(self) -> str:
        """Get the node name for OVSAccess."""
        return self._data["node_name"]
