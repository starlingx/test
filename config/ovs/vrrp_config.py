"""Typed VRRP configuration for OVS test suites."""


class VrrpConfig:
    """Typed VRRP configuration for a specific VLAN.

    Accessed via OvsConfig.get_vrrp_config(vlan_key).
    """

    def __init__(self, vrrp_dict: dict):
        """Initialize from a VRRP dictionary entry.

        Args:
            vrrp_dict: Dict with keys vip_v4, vip_v6, host_v4, host_v6, vlan_id.
        """
        self._data = vrrp_dict

    def get_vip_v4(self) -> str:
        """Get IPv4 virtual IP."""
        return self._data["vip_v4"]

    def get_vip_v6(self) -> str:
        """Get IPv6 virtual IP."""
        return self._data["vip_v6"]

    def get_host_v4(self) -> str:
        """Get IPv4 host address."""
        return self._data["host_v4"]

    def get_host_v6(self) -> str:
        """Get IPv6 host address."""
        return self._data["host_v6"]

    def get_vlan_id(self) -> int:
        """Get VLAN ID as integer."""
        return int(self._data["vlan_id"])
