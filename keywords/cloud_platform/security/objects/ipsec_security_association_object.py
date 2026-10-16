import ipaddress
import re
from typing import Union


class IPSecSecurityAssociationObject:
    """Represents a single IPSec security association."""

    def __init__(self, name: str, association_data: str):
        """Initialize the security association object.

        Args:
            name (str): Name of the association.
            association_data (str): Raw association data from swanctl output.
        """
        self._name = name.strip() if name else ""
        self._association_data = association_data or ""
        self._local_cns = self._extract_cns("local")
        self._remote_cns = self._extract_cns("remote")
        self._remote_cns_set = set(self._remote_cns)
        self._local_ips = self._extract_ips("local")
        self._remote_ips = self._extract_ips("remote")

    def get_name(self) -> str:
        """Get the association name.

        Returns:
            str: Association name.
        """
        return self._name

    def get_association_data(self) -> str:
        """Get the raw association data.

        Returns:
            str: Raw association data.
        """
        return self._association_data

    def is_established(self) -> bool:
        """Check if the connection is established.

        Returns:
            bool: True if connection is established, False otherwise.
        """
        return re.search(r"\bESTABLISHED\b", self._association_data) is not None

    def get_local_cns(self) -> list[str]:
        """Get local Common Names.

        Returns:
            list[str]: List of local CNs.
        """
        return self._local_cns

    def get_remote_cns(self) -> list[str]:
        """Get remote Common Names.

        Returns:
            list[str]: List of remote CNs.
        """
        return self._remote_cns

    def has_local_cn_starting_with(self, prefix: str) -> bool:
        """Check if any local CN starts with the given prefix.

        Args:
            prefix (str): Prefix to check for.

        Returns:
            bool: True if any local CN starts with prefix, False otherwise.
        """
        if not prefix or not prefix.strip():
            return False
        return any(cn.startswith(prefix.strip()) for cn in self._local_cns)

    def has_remote_cn_in_set(self, cn_set: Union[set, list]) -> bool:
        """Check if any remote CN is in the given set.

        Args:
            cn_set (Union[set, list]): Set or list of CNs to check against.

        Returns:
            bool: True if any remote CN is in the set, False otherwise.
        """
        if not cn_set:
            return False
        return bool(self._remote_cns_set & (set(cn_set) if isinstance(cn_set, list) else cn_set))

    def get_local_ips(self) -> list[str]:
        """Get local endpoint IP addresses.

        Parses the IP addresses from the local peer identity lines in the
        swanctl output (for example, local 'CN=..' @ <ip>[500]).

        Returns:
            list[str]: List of local endpoint IP addresses.
        """
        return self._local_ips

    def get_remote_ips(self) -> list[str]:
        """Get remote endpoint IP addresses.

        Parses the IP addresses from the remote peer identity lines in the
        swanctl output (for example, remote 'CN=..' @ <ip>[500]).

        Returns:
            list[str]: List of remote endpoint IP addresses.
        """
        return self._remote_ips

    def has_local_ip_in_set(self, ip_set: Union[set, list]) -> bool:
        """Check if any local endpoint IP is in the given set.

        Args:
            ip_set (Union[set, list]): Set or list of IP addresses to check against.

        Returns:
            bool: True if any local IP is in the set, False otherwise.
        """
        if not ip_set:
            return False
        return bool(set(self._local_ips) & (set(ip_set) if isinstance(ip_set, list) else ip_set))

    def has_local_ip_in_subnet(self, subnet: str) -> bool:
        """Check that every local endpoint IP falls within the given subnet.

        The active controller's local endpoint may be its unit management address
        or the management floating address (which is not enumerated per host), so
        local endpoints are validated by management-subnet membership rather than
        against the per-host address set.

        Args:
            subnet (str): Management subnet in CIDR notation (for example a '/64' or '/24' network).

        Returns:
            bool: True if local IPs exist and all fall within the subnet, False otherwise.
        """
        if not subnet or not self._local_ips:
            return False
        network = ipaddress.ip_network(subnet, strict=False)
        return all(ipaddress.ip_address(ip) in network for ip in self._local_ips)

    def has_all_remote_ips_in_subnet(self, subnet: str) -> bool:
        """Check that every remote endpoint IP falls within the given subnet.

        Args:
            subnet (str): Management subnet in CIDR notation (for example a '/64' or '/24' network).

        Returns:
            bool: True if remote IPs exist and all fall within the subnet, False otherwise.
        """
        if not subnet or not self._remote_ips:
            return False
        network = ipaddress.ip_network(subnet, strict=False)
        return all(ipaddress.ip_address(ip) in network for ip in self._remote_ips)

    def has_all_remote_ips_in_set(self, ip_set: Union[set, list]) -> bool:
        """Check that every remote endpoint IP is in the given set.

        Args:
            ip_set (Union[set, list]): Set or list of valid management IP addresses.

        Returns:
            bool: True if remote IPs exist and all are in the set, False otherwise.
        """
        if not ip_set or not self._remote_ips:
            return False
        allowed = set(ip_set) if isinstance(ip_set, list) else ip_set
        return all(ip in allowed for ip in self._remote_ips)

    def _extract_cns(self, cn_type: str) -> list[str]:
        """Extract Common Names from association data.

        Args:
            cn_type (str): Type of CN to extract (local or remote).

        Returns:
            list[str]: List of CNs.
        """
        pattern = rf"{cn_type}\s+'CN=([^']*)'(?:\s|$)"
        return re.findall(pattern, self._association_data)

    def _extract_ips(self, ip_type: str) -> list[str]:
        """Extract endpoint IP addresses from association data.

        Matches the swanctl peer identity format where the IP (IPv4 or IPv6)
        follows the CN and precedes the IKE port, e.g. "local 'CN=..' @ <ip>[500]".

        Args:
            ip_type (str): Type of endpoint to extract (local or remote).

        Returns:
            list[str]: List of endpoint IP addresses.
        """
        pattern = rf"{ip_type}\s+'CN=[^']*'\s+@\s+([0-9a-fA-F:.]+)\[\d+\]"
        return re.findall(pattern, self._association_data)
