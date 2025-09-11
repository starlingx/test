import re

from keywords.network.ip_address_keywords import IPAddressKeywords


class IPSecDnsmasqObject:
    """Object representing a dnsmasq.hosts entry."""

    def __init__(self, mac_address: str, pxeboot_name: str, pxeboot_address: str):
        """Initialize dnsmasq entry object.

        Args:
            mac_address (str): MAC address.
            pxeboot_name (str): PXE boot hostname.
            pxeboot_address (str): PXE boot IP address.
        """
        self._mac_address = mac_address
        self._pxeboot_name = pxeboot_name
        self._pxeboot_address = pxeboot_address

    def get_mac_address(self) -> str:
        """Get MAC address.

        Returns:
            str: MAC address.
        """
        return self._mac_address

    def get_pxeboot_name(self) -> str:
        """Get PXE boot hostname.

        Returns:
            str: PXE boot hostname.
        """
        return self._pxeboot_name

    def get_pxeboot_address(self) -> str:
        """Get PXE boot IP address.

        Returns:
            str: PXE boot IP address.
        """
        return self._pxeboot_address

    def is_valid_mac(self) -> bool:
        """Check if MAC address format is valid.

        Returns:
            bool: True if MAC address format is valid.
        """
        mac_pattern = r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
        return bool(re.match(mac_pattern, self._mac_address))

    def is_pxeboot_entry(self) -> bool:
        """Check if this is a PXE boot entry.

        Returns:
            bool: True if name contains 'pxeboot-'.
        """
        return "pxeboot-" in self._pxeboot_name

    def is_valid_ip_address(self) -> bool:
        """Check if PXE boot address is a valid IP address using framework method.

        Returns:
            bool: True if address is a valid IPv4 address.
        """
        try:
            # Use existing framework method for IP validation
            IPAddressKeywords(self._pxeboot_address)
            return True
        except ValueError:
            return False
