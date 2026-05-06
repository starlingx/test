"""Object representing TLS endpoint IP information."""


class TlsEndpointIpsObject:
    """Structured object for endpoint IP information returned by TlsKeywords.get_endpoint_ips()."""

    def __init__(self, oam_ip: str, mgmt_ip: str, is_ipv6: bool):
        """Initialize TLS endpoint IPs object.

        Args:
            oam_ip (str): OAM floating IP address.
            mgmt_ip (str): Management floating IP address.
            is_ipv6 (bool): Whether the lab uses IPv6 addressing.
        """
        self._oam_ip = oam_ip
        self._mgmt_ip = mgmt_ip
        self._is_ipv6 = is_ipv6

    def get_oam_ip(self) -> str:
        """Getter for OAM floating IP.

        Returns:
            str: OAM floating IP address.
        """
        return self._oam_ip

    def get_mgmt_ip(self) -> str:
        """Getter for management floating IP.

        Returns:
            str: Management floating IP address.
        """
        return self._mgmt_ip

    def is_ipv6_lab(self) -> bool:
        """Check if the lab uses IPv6 addressing.

        Returns:
            bool: True if the lab uses IPv6.
        """
        return self._is_ipv6
