"""Networking test configuration.

Provides access to networking-specific test parameters from the lab config
file, under the optional top-level "networking" section. All lab-specific
values are loaded at runtime, keeping test code portable across different
lab environments.

Accessed via ConfigurationManager.get_lab_config().get_networking_config().

Example lab_config.json5 section:

    "networking": {
        // VLAN ID used to tag the network-attachment-definitions created by
        // the cross-host SR-IOV device plugin tests. It MUST be a VLAN that
        // the lab's data-network top-of-rack switch trunks on the SR-IOV
        // data ports; otherwise cross-host traffic is dropped and the tests
        // fail. Leave unset to use the test default.
        "sriov_test_vlan": 2692
    }
"""

from typing import Optional


class NetworkingConfig:
    """Networking test configuration parsed from the lab config networking section.

    Access pattern:
        from config.configuration_manager import ConfigurationManager
        networking_config = ConfigurationManager.get_lab_config().get_networking_config()
    """

    def __init__(self, networking_dict: dict):
        """Initialize from the networking dictionary in the lab config.

        Args:
            networking_dict (dict): The networking section from the lab config file.
        """
        self.sriov_test_vlan: Optional[int] = networking_dict.get("sriov_test_vlan", None)

    def get_sriov_test_vlan(self) -> Optional[int]:
        """Get the SR-IOV test VLAN ID.

        VLAN ID used to tag the network-attachment-definitions created by the
        cross-host SR-IOV device plugin tests. It must be a VLAN that the lab's
        data-network top-of-rack switch trunks on the SR-IOV data ports.

        Returns:
            Optional[int]: The configured SR-IOV test VLAN, or None if not set.
        """
        return self.sriov_test_vlan
