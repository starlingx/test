"""Keywords for IPv6 route operations including NAT64 route discovery."""

import ipaddress
from typing import Tuple

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword


class IPRouteKeywords(BaseKeyword):
    """Keywords for ip route operations on a Linux host."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def resolve_hostname(self, hostname: str) -> str:
        """Resolve a hostname to its IP address using getent.

        Args:
            hostname (str): Hostname to resolve.

        Returns:
            str: Resolved IP address.

        Raises:
            ValueError: If hostname cannot be resolved.
        """
        output = self.ssh_connection.send(f"getent hosts {hostname}")
        self.validate_success_return_code(self.ssh_connection)

        for line in output:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                parts = stripped.split()
                if parts:
                    return parts[0]

        raise ValueError(f"Cannot resolve hostname '{hostname}'")

    def get_route_gateway(self, destination_ip: str) -> str:
        """Get the gateway for a specific destination IP from the routing table.

        Runs 'ip -6 route get <destination_ip>' and parses the 'via' gateway.

        Args:
            destination_ip (str): Destination IP address to look up.

        Returns:
            str: Gateway address for the destination.

        Raises:
            ValueError: If no gateway can be determined for the destination.
        """
        output = self.ssh_connection.send(f"ip -6 route get {destination_ip}")
        self.validate_success_return_code(self.ssh_connection)

        for line in output:
            stripped = line.strip()
            if "via" in stripped:
                parts = stripped.split()
                via_idx = parts.index("via")
                if via_idx + 1 < len(parts):
                    return parts[via_idx + 1]

        raise ValueError(f"Cannot determine gateway for '{destination_ip}' from routing table")

    def get_nat64_route_details(self, registry_ip: str) -> Tuple[str, str]:
        """Get NAT64 route prefix and gateway suffix from the routing table.

        Discovers the NAT64 route by looking up the registry IP's gateway,
        extracting the suffix, and finding the route prefix in the table.

        Args:
            registry_ip (str): IPv6 address of the target (e.g., external registry).

        Returns:
            Tuple[str, str]: (nat64_prefix, gateway_suffix) where:
                - nat64_prefix: Route prefix in CIDR notation (e.g., "64:ff9b::/96")
                - gateway_suffix: Host part of the via gateway (e.g., "6:0")

        Raises:
            ValueError: If the NAT64 route cannot be determined.
        """
        gateway = self.get_route_gateway(registry_ip)
        get_logger().log_info(f"NAT64 gateway for '{registry_ip}': {gateway}")

        # Extract gateway suffix (e.g. "<subnet>::6:0" -> "6:0")
        if "::" in gateway:
            gateway_suffix = gateway.split("::")[1]
        else:
            gateway_suffix = gateway.rsplit(":", 2)[-2] + ":" + gateway.rsplit(":", 1)[-1]

        # Get the prefix from the routing table
        prefix_hint = registry_ip.split("::")[0] if "::" in registry_ip else registry_ip.rsplit(":", 1)[0]
        output = self.ssh_connection.send(f"ip -6 route | grep '{prefix_hint}'")

        for line in output:
            stripped = line.strip()
            if "/" in stripped:
                nat64_prefix = stripped.split()[0]
                return nat64_prefix, gateway_suffix

        # Fallback: build /64 prefix from the IP
        addr = ipaddress.ip_address(registry_ip)
        network = ipaddress.ip_network(f"{addr}/64", strict=False)
        return str(network), gateway_suffix

    def add_ipv6_route(self, prefix: str, gateway: str, interface: str, source_ip: str, password: str) -> None:
        """Add an IPv6 route on the host.

        Args:
            prefix (str): Route prefix in CIDR notation.
            gateway (str): Gateway IPv6 address.
            interface (str): Network interface name.
            source_ip (str): Source IP for the route.
            password (str): Password for sudo.
        """
        cmd = f"echo '{password}' | sudo -S ip route add {prefix} via {gateway} dev {interface} src {source_ip} metric 1 pref medium"
        self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info(f"Route added: {prefix} via {gateway} dev {interface} src {source_ip}")

    def verify_connectivity(self, target_ip: str, count: int = 3, timeout: int = 5) -> bool:
        """Verify connectivity to a target IP via ping.

        Args:
            target_ip (str): IP address to ping.
            count (int): Number of ping packets. Defaults to 3.
            timeout (int): Ping timeout in seconds. Defaults to 5.

        Returns:
            bool: True if ping succeeds, False otherwise.
        """
        self.ssh_connection.send(f"ping -c {count} -W {timeout} {target_ip}")
        return self.ssh_connection.get_return_code() == 0

    def verify_connectivity_with_retry(self, target_ip: str, description: str, retry_timeout: int = 30, polling_sleep_time: int = 5) -> None:
        """Verify connectivity to a target IP with retry.

        Uses validate_equals_with_retry for robustness after route addition.

        Args:
            target_ip (str): IP address to ping.
            description (str): Description for validation logging.
            retry_timeout (int): Total time to retry. Defaults to 30.
            polling_sleep_time (int): Interval between retries. Defaults to 5.
        """
        validate_equals_with_retry(
            lambda: self.verify_connectivity(target_ip),
            True,
            description,
            timeout=retry_timeout,
            polling_sleep_time=polling_sleep_time,
        )

    @staticmethod
    def build_nat64_gateway(oam_ip: str, gateway_suffix: str) -> str:
        """Build the NAT64 gateway address from an OAM IP and gateway suffix.

        Args:
            oam_ip (str): Host OAM IPv6 address.
            gateway_suffix (str): Gateway host suffix from system controller route.

        Returns:
            str: NAT64 gateway address for the host.
        """
        if "::" in oam_ip:
            subnet_prefix = oam_ip.split("::")[0]
        else:
            parts = oam_ip.split(":")
            subnet_prefix = ":".join(parts[:4])

        return f"{subnet_prefix}::{gateway_suffix}"
