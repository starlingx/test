import ipaddress
import socket
from typing import Optional

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword


class IPAddressKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the Internet Protocol (IP) addresses in a general way, that is it,

    independently of specific implemented technologies.
    """

    def __init__(self, ip: str):
        """
        Constructor

        Args:
            ip (str): a valid IPv4 or IPv6 address representation.
        """
        self.ip = None

        if not self.is_valid_ip_address(ip):
            raise ValueError(f"{ip} is not a valid IPv4 or IPv6 address.")

        self.ip = ip

    def ipv6_same_network(self, ipv6: str, prefix_length: int) -> bool:
        """
        Verifies if 'ipv6' and 'self.ip' addresses belong to the same network.

        Args:
            ipv6 (str): An IPv6 address as a string.
            prefix_length (int): The prefix length (network mask).

        Returns:
            bool: True if 'self.ip' and 'ipv6' are in the same network, False otherwise.

        """
        if not self.is_valid_ip_address(ipv6):
            raise ValueError(f"{ipv6} is not a valid IPv6 address.")

        # Convert IPv6 address to IPv6Address objects.
        net1 = ipaddress.IPv6Network(f"{self.ip}/{prefix_length}", strict=False)
        net2 = ipaddress.IPv6Network(f"{ipv6}/{prefix_length}", strict=False)

        return net1.network_address == net2.network_address

    def ipv4_same_network(self, ipv4: str, netmask: str) -> bool:
        """
        Verifies if 'ipv4' and 'self.ip' addresses belong to the same network.

        Args:
            ipv4 (str): An IPv6 address as a string.
            netmask (str): The subnet mask as a string.

        Returns:
            bool: True if 'self.ip' and 'ipv4' are in the same network, False otherwise.

        """
        if not self.is_valid_ip_address(ipv4):
            raise ValueError(f"{ipv4} is not a valid IPv4 address.")

        # Convert IPv4 addresses and netmask to integer format
        ip1 = int(ipaddress.IPv4Address(self.ip))
        ip2 = int(ipaddress.IPv4Address(ipv4))
        mask = int(ipaddress.IPv4Address(netmask))

        # Apply netmask to both IPs and compare if they are in the same network
        return (ip1 & mask) == (ip2 & mask)

    def ipv4_with_prefix_length_same_network(self, ipv4: str, prefix_length: int) -> bool:
        """
        Verifies if 'ipv4' and 'self.ip' addresses belong to the same network.

        Args:
            ipv4 (str): An IPv6 address as a string.
            prefix_length (int): The number of leading bits that corresponds to the network prefix in the IP address.

        Returns:
            bool: True if 'self.ip' and 'ipv4' are in the same network; False otherwise.

        """
        if not self.is_valid_ip_address(ipv4):
            raise ValueError(f"{ipv4} is not a valid IPv4 address.")

        ip1 = ipaddress.IPv4Interface(f"{self.ip}/{prefix_length}")
        ip2 = ipaddress.IPv4Interface(f"{ipv4}/{prefix_length}")

        return ip1.network == ip2.network

    def ip_same_network(self, ip: str, prefix_length: int) -> bool:
        """
        Verifies if 'ipv6' and 'self.ip' addresses belong to the same network.

        Args:
            ip (str): An IPv4 or IPv6 address as a string.
            prefix_length (int): The prefix length.

        Returns:
            bool: True if 'self.ip' and 'ip' are in the same network; False otherwise.

        """
        if not self.is_valid_ip_address(ip):
            return False

        if self.check_ip_version(self.ip) != self.check_ip_version(ip):
            return False

        ip_version = self.check_ip_version(ip)
        if ip_version == "IPv4":
            return self.ipv4_with_prefix_length_same_network(ip, prefix_length)
        elif ip_version == "IPv6":
            return self.ipv6_same_network(ip, prefix_length)
        else:
            return False

    def is_valid_ip_address(self, ip_address: str) -> bool:
        """
        Check if 'ip_address' is a valid IPv4 or IPv6 address.

        Args:
            ip_address (str): a supposed valid either IPv4 or IPv6 address.

        Returns:
            bool: True if 'ip_address' is valid IP; False otherwise.
        """
        try:
            ipaddress.ip_address(ip_address)
            return True
        except ValueError:
            return False

    def check_ip_version(self, ip: str) -> Optional[str]:
        """
        Check if 'ip' is either an IPv4 or IPv6 address.

        Args:
            ip (str): a supposed valid either IPv4 or IPv6 address.

        Returns:
            Optional[str]: 'IPv4' if the address is IPv4, 'IPv6' if the address is IPv6, or None if invalid.
        """
        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError:
            return None

        if ip_obj.version == 4:
            return "IPv4"
        elif ip_obj.version == 6:
            return "IPv6"

    def check_dnsname_resolution(self, dns_name: str) -> bool:
        """
        Method to verify the DNS name resolution.

        Args:
            dns_name (str): DNS name to resolve.

        Returns:
            bool: True if the DNS name resolves to an IP address, False otherwise.
        """
        family = socket.AF_INET
        if self.check_ip_version(self.ip) == "IPv6":
            family = socket.AF_INET6
        try:
            socket.getaddrinfo(dns_name, None, family)
            return True
        except socket.error as msg:
            get_logger().log_error(f"nslookup failed with error '{msg}'")
            return False
