import ipaddress
import re


class IPObject:
    """
    Class that represents an IP address, including the IP itself and its prefix length (subnet network).
    """

    def __init__(self, ip_with_prefix: str):
        """
        Constructor

        Args:
            ip_with_prefix (str): An IP address, either version 4 or 6, followed or not by /<prefix length>.
        """
        # Gets the IP from an IP with prefix length. Example: gets '192.168.1.1' from '192.168.1.1/24'.
        self.ip_address = IPObject._extract_ip_address(ip_with_prefix)

        # Gets the 'prefix length' from the ip address. Example: Gets the '24' from '192.168.1.1/24'
        self.prefix_length = IPObject._extract_prefix_length(ip_with_prefix)

        if not ipaddress.ip_address(self.ip_address):
            raise ValueError(f"The argument {ip_with_prefix} must be a valid IPv4 or IPv6 address.")

    def set_ip_address(self, ip_address: str) -> None:
        """
        Setter for ip_address property

        Args:
            ip_address (str): a string representing an IPv4 or IPv6 address either with prefix length or without prefix length, the prefix length will be discarded if present.
        """
        if ipaddress.ip_address(ip_address):
            raise ValueError(f"The argument {ip_address} must be a valid IPv4 or IPv6 address.")
        self.ip_address = IPObject._extract_ip_address(ip_address)

    def get_ip_address(self) -> str:
        """
        Getter for ip_address property

        Returns:
            str: ip_address
        """
        return self.ip_address

    def set_prefix_length(self, prefix_length: int):
        """
        Setter for prefix_length property

        Args:
            prefix_length (int): an prefix length number.
        """
        self.prefix_length = prefix_length

    def get_prefix_length(self) -> int:
        """
        Getter for prefix length property

        Returns:
            int: prefix length number
        """
        return self.prefix_length

    @staticmethod
    def _extract_ip_address(ip_address_with_prefix: str) -> str:
        """
        Extracts the IP address from an IP with prefix length.

        Example: gets '192.168.1.1' from '192.168.1.1/24'.

        Args:
            ip_address_with_prefix (str): an IP address with prefix length.

        Returns:
            str: an ip_address without prefix length.
        """
        return re.sub(r"/\d+", "", ip_address_with_prefix)

    @staticmethod
    def _extract_prefix_length(ip_address_with_prefix: str) -> int:
        """
        Extracts the prefix length from an IP with prefix length.

        Example: gets 24 from '192.168.1.1/24'.

        Args:
            ip_address_with_prefix (str): an IP address with prefix length.

        Returns:
            int: the prefix_length of the IP passed as argument.
        """
        prefix_length = 0
        match = re.search(r"/(\d+)", ip_address_with_prefix)
        if match:
            prefix_length = int(match.group(1))
        return prefix_length
