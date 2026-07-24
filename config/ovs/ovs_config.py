"""OVS test configuration.

Provides access to OVS-specific test parameters from the lab config file.
Accessed via ConfigurationManager.get_lab_config().get_ovs_config().
All lab-specific values (IPs, VLANs, VRRP VIPs) are loaded at runtime,
keeping test code portable across different lab environments.
"""


class OvsConfig:
    """OVS test configuration parsed from the lab config 'ovs' section.

    Access pattern:
        from config.configuration_manager import ConfigurationManager
        ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    """

    def __init__(self, ovs_dict: dict, admin_password: str = ""):
        """Initialize from the 'ovs' dictionary in the lab config.

        Args:
            ovs_dict: The 'ovs' section from default.json5.
            admin_password: Admin password from lab config credentials.
        """
        self.remote_peer_ip: str = ovs_dict.get("remote_peer_ip", "")
        self.bridge_name: str = ovs_dict.get("bridge_name", "br-sriov")
        self.namespace: str = ovs_dict.get("namespace", "openvswitch")
        self.ports: list = ovs_dict.get("ports", [])
        self.bridge_ips: dict = ovs_dict.get("bridge_ips", {})
        self.peer_ips: dict = ovs_dict.get("peer_ips", {})
        self.vrrp: dict = ovs_dict.get("vrrp", {})
        self.bfd_interfaces: list = ovs_dict.get("bfd_interfaces", [])
        self.helm_overrides: dict = ovs_dict.get("helm_overrides", {})
        self.traffic_pod_prefix: str = ovs_dict.get("traffic_pod_prefix", "pod1-deployment")
        self._admin_password: str = admin_password

    def get_remote_peer_ip(self) -> str:
        """Get the remote peer IP address."""
        return self.remote_peer_ip

    def get_remote_peer_password(self) -> str:
        """Get the remote peer password (same admin credentials as primary lab)."""
        return self._admin_password

    def get_bridge_name(self) -> str:
        """Get the OVS bridge name."""
        return self.bridge_name

    def get_namespace(self) -> str:
        """Get the OVS application namespace."""
        return self.namespace

    def get_ports(self) -> list:
        """Get the list of OVS port names."""
        return self.ports

    def get_bridge_ip(self, vlan_key: str) -> str:
        """Get a bridge IP for the given VLAN key (e.g., 'untagged', 'vlan100')."""
        return self.bridge_ips.get(vlan_key, "")

    def get_peer_ip(self, vlan_key: str) -> str:
        """Get a peer IP for the given VLAN key (e.g., 'untagged', 'vlan100')."""
        return self.peer_ips.get(vlan_key, "")

    def get_vrrp_config(self, vlan_key: str) -> dict:
        """Get VRRP config for a VLAN key (e.g., 'vlan702').

        Returns dict with keys: vip_v4, vip_v6, host_v4, host_v6, vlan_id
        """
        return self.vrrp.get(vlan_key, {})

    def get_bfd_interfaces(self) -> list:
        """Get the list of BFD-enabled interface names."""
        return self.bfd_interfaces

    def get_helm_overrides(self) -> dict:
        """Get helm override image/tag configuration."""
        return self.helm_overrides

    def get_traffic_pod_prefix(self) -> str:
        """Get the traffic pod name prefix on the remote peer."""
        return self.traffic_pod_prefix
