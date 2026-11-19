"""Object for one IP pool of the Calico Installation CR."""

import ipaddress
from typing import Optional


class InstallationIPPoolObject:
    """One entry of spec.calicoNetwork.ipPools in the default Installation CR."""

    def __init__(self, name: Optional[str], cidr: str, block_size: Optional[int], encapsulation: Optional[str], nat_outgoing: Optional[str], node_selector: Optional[str]):
        """Initialize the IP pool.

        Args:
            name (Optional[str]): The pool name, if set.
            cidr (str): The pool CIDR (e.g. '172.16.0.0/16').
            block_size (Optional[int]): The block size, if set.
            encapsulation (Optional[str]): The encapsulation (e.g. 'None', 'VXLAN', 'IPIP'), if set.
            nat_outgoing (Optional[str]): 'Enabled' or 'Disabled', if set.
            node_selector (Optional[str]): The node selector (e.g. 'all()'), if set.
        """
        self.name = name
        self.cidr = cidr
        self.block_size = block_size
        self.encapsulation = encapsulation
        self.nat_outgoing = nat_outgoing
        self.node_selector = node_selector

    def get_name(self) -> Optional[str]:
        """Get the pool name.

        Returns:
            Optional[str]: The pool name, or None when it is not set.
        """
        return self.name

    def get_cidr(self) -> str:
        """Get the pool CIDR.

        Returns:
            str: The pool CIDR.
        """
        return self.cidr

    def get_block_size(self) -> Optional[int]:
        """Get the pool block size.

        Returns:
            Optional[int]: The block size, or None when it is not set.
        """
        return self.block_size

    def get_encapsulation(self) -> Optional[str]:
        """Get the pool encapsulation.

        Returns:
            Optional[str]: The encapsulation, or None when it is not set.
        """
        return self.encapsulation

    def get_nat_outgoing(self) -> Optional[str]:
        """Get the pool NAT outgoing setting.

        Returns:
            Optional[str]: 'Enabled' or 'Disabled', or None when it is not set.
        """
        return self.nat_outgoing

    def get_node_selector(self) -> Optional[str]:
        """Get the pool node selector.

        Returns:
            Optional[str]: The node selector, or None when it is not set.
        """
        return self.node_selector

    def get_ip_version(self) -> int:
        """Get the IP version of the pool CIDR.

        Returns:
            int: 4 or 6.
        """
        return ipaddress.ip_network(self.cidr, strict=False).version

    def contains_ip(self, ip: str) -> bool:
        """Check whether an IP address is inside the pool CIDR.

        Args:
            ip (str): The IP address to check.

        Returns:
            bool: True if the address is inside the pool CIDR, False otherwise.
        """
        return ipaddress.ip_address(ip) in ipaddress.ip_network(self.cidr, strict=False)

    def __str__(self) -> str:
        """Human-readable representation of the IP pool.

        Returns:
            str: The pool name, CIDR and main settings.
        """
        return f"InstallationIPPoolObject(name={self.name}, cidr={self.cidr}, block_size={self.block_size}, encapsulation={self.encapsulation}, nat_outgoing={self.nat_outgoing})"
