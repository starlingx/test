"""OVS test configuration.

Provides access to OVS-specific test parameters from the lab config file.
Accessed via ConfigurationManager.get_lab_config().get_ovs_config().
All lab-specific values (IPs, VLANs, VRRP VIPs) are loaded at runtime,
keeping test code portable across different lab environments.
"""

from config.ovs.ovs_access_config import OvsAccessConfig
from config.ovs.sriov_interface_config import SriovInterfaceConfig
from config.ovs.vrrp_config import VrrpConfig


class OvsConfig:
    """OVS test configuration parsed from the lab config ovs section.

    Access pattern:
        from config.configuration_manager import ConfigurationManager
        ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    """

    def __init__(self, ovs_dict: dict, admin_password: str = ""):
        """Initialize from the ovs dictionary in the lab config.

        Args:
            ovs_dict: The ovs section from the lab config file.
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
        self.sriov_interfaces: list = ovs_dict.get("sriov_interfaces", [])
        self.traffic_pod_prefix: str = ovs_dict.get("traffic_pod_prefix", "pod1-deployment")
        self.ovsaccess: dict = ovs_dict.get("ovsaccess", {})
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
        """Get a bridge IP for the given VLAN key (e.g., untagged, vlan100)."""
        return self.bridge_ips.get(vlan_key, "")

    def get_bridge_ips(self) -> dict:
        """Get all bridge IPs as a dict of vlan_key -> IP address."""
        return self.bridge_ips

    def get_peer_ip(self, vlan_key: str) -> str:
        """Get a peer IP for the given VLAN key (e.g., untagged, vlan100)."""
        return self.peer_ips.get(vlan_key, "")

    def get_peer_ips(self) -> dict:
        """Get all peer IPs as a dict of vlan_key -> IP address."""
        return self.peer_ips

    def get_vrrp_config(self, vlan_key: str) -> VrrpConfig:
        """Get typed VRRP config for a VLAN key.

        Args:
            vlan_key: VLAN identifier (e.g., vlan110, oru_oam).

        Returns:
            VrrpConfig: Typed config object with getters.
        """
        return VrrpConfig(self.vrrp[vlan_key])

    def get_bfd_interfaces(self) -> list:
        """Get the list of BFD-enabled interface names."""
        return self.bfd_interfaces

    def get_helm_overrides(self) -> dict:
        """Get helm override image/tag configuration."""
        return self.helm_overrides

    def get_sriov_interfaces(self) -> list:
        """Get the list of SR-IOV interface configurations.

        Each entry is a SriovInterfaceConfig with typed getters.
        Used by ensure_ovs_setup to provision SR-IOV on fresh installs.

        Returns:
            list[SriovInterfaceConfig]: Typed SR-IOV interface configs.

        Example config:
            "sriov_interfaces": [
                {"port_name": "ens2f0", "num_vfs": 8, "vf_driver": "netdevice", "mtu": 1500},
                {"port_name": "ens2f1", "num_vfs": 8, "vf_driver": "netdevice", "mtu": 1500}
            ]
        """
        return [SriovInterfaceConfig(cfg) for cfg in self.sriov_interfaces]

    def get_traffic_pod_prefix(self) -> str:
        """Get the traffic pod name prefix on the remote peer."""
        return self.traffic_pod_prefix

    def get_ovsaccess_config(self) -> OvsAccessConfig:
        """Get typed OVSAccess test configuration.

        Returns:
            OvsAccessConfig: Typed config with get_interface_name()/get_node_name().
        """
        return OvsAccessConfig(self.ovsaccess)
