"""SR-IOV interface configuration for OVS setup.

Typed config object for SR-IOV interface parameters, consistent with
VrrpConfig and OvsAccessConfig patterns.
"""


class SriovInterfaceConfig:
    """Typed SR-IOV interface configuration from the lab config.

    Example config entry:
        {"port_name": "ens2f0", "num_vfs": 8, "vf_driver": "netdevice", "mtu": 1500}
    """

    def __init__(self, sriov_dict: dict):
        """Initialize from an SR-IOV interface dictionary.

        Args:
            sriov_dict: Dictionary with SR-IOV interface parameters.
        """
        self._data = sriov_dict

    def get_port_name(self) -> str:
        """Get the physical port name to configure as pci-sriov.

        Returns:
            str: Port name (e.g., 'ens2f0', 'enp108s0f0').
        """
        return self._data["port_name"]

    def get_num_vfs(self) -> int:
        """Get the number of VFs to configure.

        Returns:
            int: Number of VFs (default 8).
        """
        return self._data.get("num_vfs", 8)

    def get_vf_driver(self) -> str:
        """Get the VF driver type.

        Returns:
            str: VF driver (default 'netdevice').
        """
        return self._data.get("vf_driver", "netdevice")

    def get_mtu(self) -> int:
        """Get the MTU value.

        Returns:
            int: MTU value (default 1500).
        """
        return self._data.get("mtu", 1500)
