"""Object for one BGP peer row of 'calico-node -show-status'."""


class CalicoNodeBgpPeerObject:
    """One row of a 'bird vX BGP peers' table from 'calico-node -show-status'."""

    def __init__(self, ip_version: str, peer_address: str):
        """Initialize the BGP peer object.

        Args:
            ip_version (str): The bird instance the peer belongs to ('v4' or 'v6').
            peer_address (str): The peer IP address.
        """
        self.ip_version = ip_version
        self.peer_address = peer_address
        self.peer_type = ""
        self.state = ""
        self.bgp_state = ""

    def get_ip_version(self) -> str:
        """Get the bird instance the peer belongs to.

        Returns:
            str: 'v4' or 'v6'.
        """
        return self.ip_version

    def get_peer_address(self) -> str:
        """Get the peer IP address.

        Returns:
            str: The peer IP address.
        """
        return self.peer_address

    def set_peer_type(self, peer_type: str) -> None:
        """Set the peer type.

        Args:
            peer_type (str): The peer type (e.g. 'node-to-node mesh').
        """
        self.peer_type = peer_type

    def get_peer_type(self) -> str:
        """Get the peer type.

        Returns:
            str: The peer type (e.g. 'node-to-node mesh').
        """
        return self.peer_type

    def set_state(self, state: str) -> None:
        """Set the peer session state.

        Args:
            state (str): The session state (e.g. 'up').
        """
        self.state = state

    def get_state(self) -> str:
        """Get the peer session state.

        Returns:
            str: The session state (e.g. 'up').
        """
        return self.state

    def set_bgp_state(self, bgp_state: str) -> None:
        """Set the BGP state.

        Args:
            bgp_state (str): The BGP state (e.g. 'Established').
        """
        self.bgp_state = bgp_state

    def get_bgp_state(self) -> str:
        """Get the BGP state.

        Returns:
            str: The BGPSTATE column value (e.g. 'Established').
        """
        return self.bgp_state

    def is_established(self) -> bool:
        """Check whether the BGP session is Established.

        Returns:
            bool: True if the BGP state is 'Established'.
        """
        return self.bgp_state == "Established"

    def __str__(self) -> str:
        """Human-readable representation of the peer.

        Returns:
            str: The peer address, IP version and BGP state.
        """
        return f"{self.peer_address} ({self.ip_version}, {self.bgp_state})"
