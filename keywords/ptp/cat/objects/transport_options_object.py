class TransportOptionsObject:
    """
    Object to hold the values of Transport Options Object
    """

    def __init__(self):
        self.transport_specific: str = ''
        self.ptp_dst_mac: str = ''
        self.p2p_dst_mac: str = ''
        self.udp_ttl: int = -1
        self.udp6_scope: str = ''
        self.uds_address: str = ''
        self.uds_ro_address: str = ''

    def get_transport_specific(self) -> str:
        """
        Getter for transport_specific
        Returns: transport_specific

        """
        return self.transport_specific

    def set_transport_specific(self, transport_specific: str):
        """
        Setter for transport_specific
        Args:
            transport_specific (): the transport_specific value

        Returns:

        """
        self.transport_specific = transport_specific

    def get_ptp_dst_mac(self) -> str:
        """
        Getter for ptp_dst_mac
        Returns: ptp_dst_mac value

        """
        return self.ptp_dst_mac

    def set_ptp_dst_mac(self, ptp_dst_mac: str):
        """
        Setter for ptp_dst_mac
        Args:
            ptp_dst_mac (): ptp_dst_mac value

        Returns:

        """
        self.ptp_dst_mac = ptp_dst_mac

    def get_p2p_dst_mac(self) -> str:
        """
        Getter for p2p_dst_mac
        Returns: p2p_dst_mac value

        """
        return self.p2p_dst_mac

    def set_p2p_dst_mac(self, p2p_dst_mac: str):
        """
        Setter for p2p_dst_mac
        Args:
            p2p_dst_mac (): p2p_dst_mac value

        Returns:

        """
        self.p2p_dst_mac = p2p_dst_mac

    def get_udp_ttl(self) -> int:
        """
        Getter for udp_ttl
        Returns: the udp_ttl value

        """
        return self.udp_ttl

    def set_udp_ttl(self, udp_ttl: int):
        """
        Setter for udp_ttl
        Args:
            udp_ttl (): the udp_ttl value

        Returns:

        """
        self.udp_ttl = udp_ttl

    def get_udp6_scope(self) -> str:
        """
        Getter for udp6_scope
        Returns: udp6_scope value

        """
        return self.udp6_scope

    def set_udp6_scope(self, udp6_scope: str):
        """
        Setter for udp6_scope
        Args:
            udp6_scope (): the udp6_scope value

        Returns:

        """
        self.udp6_scope = udp6_scope

    def get_uds_address(self) -> str:
        """
        Getter for uds_address
        Returns: uds_address value

        """
        return self.uds_address

    def set_uds_address(self, uds_address: str):
        """
        Setter for uds_address
        Args:
            uds_address (): the uds_address value

        Returns:

        """
        self.uds_address = uds_address

    def get_uds_ro_address(self) -> str:
        """
        Getter for uds_ro_address
        Returns: uds_ro_address value

        """
        return self.uds_ro_address

    def set_uds_ro_address(self, uds_ro_address: str):
        """
        Setter for uds_ro_address
        Args:
            uds_ro_address (): the uds_ro_address value

        Returns:

        """
        self.uds_ro_address = uds_ro_address
