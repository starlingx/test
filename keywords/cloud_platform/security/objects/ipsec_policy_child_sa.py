"""Installed policy CHILD_SA identity and traffic selectors."""

import ipaddress
import re


class IPsecPolicyChildSA:
    """An installed policy tunnel, including its IKE peer and traffic selectors."""

    def __init__(self, connection_name: str, ike: dict, child: dict):
        """Validate one installed policy CHILD_SA.

        Args:
            connection_name (str): Policy IKE connection name.
            ike (dict): Parsed VICI IKE fields.
            child (dict): Parsed VICI CHILD_SA fields.
        """
        self.connection_name = connection_name
        self.local_host = str(ipaddress.ip_address(ike["local-host"]))
        self.remote_host = str(ipaddress.ip_address(ike["remote-host"]))
        self.name = child["name"]
        self.unique_id = child["uniqueid"]
        self.local_selectors = child["local-ts"]
        self.remote_selectors = child["remote-ts"]
        self.counters = {}
        for direction in ("in", "out"):
            for unit in ("bytes", "packets"):
                field = f"{unit}-{direction}"
                value = child[field]
                if not isinstance(value, str) or not value.isdecimal():
                    raise ValueError(f"Invalid CHILD_SA counter: {field}")
                self.counters[field] = int(value)
        if not self.name or not self.unique_id or not self.local_selectors or not self.remote_selectors:
            raise ValueError("Missing CHILD_SA identity or selectors")
        for selector in self.local_selectors + self.remote_selectors:
            self._parse_selector(selector)

    @staticmethod
    def _parse_selector(selector: str) -> tuple:
        """Decode an IP network with optional protocol/port restrictions.

        Args:
            selector (str): VICI traffic selector.

        Returns:
            tuple: Network, protocol and optional inclusive port range.
        """
        match = re.fullmatch(r"([^\[\]]+)(?:\[([^/\]]+)(?:/([^\]]+))?\])?", selector)
        if not match:
            raise ValueError(f"Unsupported traffic selector: {selector}")
        network = ipaddress.ip_network(match[1], strict=False)
        protocol = {"6": "tcp", "17": "udp"}.get(match[2], match[2])
        ports = None
        if match[3] is not None:
            if not re.fullmatch(r"[0-9]+(?:-[0-9]+)?", match[3]):
                raise ValueError(f"Unsupported selector port: {selector}")
            bounds = [int(value) for value in match[3].split("-")]
            ports = (bounds[0], bounds[-1])
            if not 0 <= ports[0] <= ports[1] <= 65535:
                raise ValueError(f"Invalid selector port: {selector}")
        return network, protocol, ports

    def get_identity(self) -> tuple[str, str, str]:
        """Return an identity that distinguishes rekeyed associations.

        Returns:
            tuple[str, str, str]: Connection, CHILD name and unique ID.
        """
        return self.connection_name, self.name, self.unique_id

    def get_counters(self) -> dict[str, int]:
        """Return a copy of the observed byte and packet counters.

        Returns:
            dict[str, int]: Counters indexed by direction and unit.
        """
        return dict(self.counters)

    def matches_flow(self, local_host: str, remote_host: str, source: str, destination: str, protocol: str, port: int) -> bool:
        """Match an independently discovered outbound flow, including destination port.

        Args:
            local_host (str): Expected local cluster-host address.
            remote_host (str): Expected peer cluster-host address.
            source (str): Client pod address.
            destination (str): Server EndpointSlice address.
            protocol (str): tcp or udp.
            port (int): Server target port.

        Returns:
            bool: Whether the tunnel covers the exact requested policy flow.
        """
        if protocol not in ("tcp", "udp") or type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("A TCP/UDP flow and valid destination port are required")
        if self.local_host != str(ipaddress.ip_address(local_host)) or self.remote_host != str(ipaddress.ip_address(remote_host)):
            return False
        source_ip, destination_ip = ipaddress.ip_address(source), ipaddress.ip_address(destination)
        local_match = any(source_ip in network and proto == protocol and ports is None for network, proto, ports in map(self._parse_selector, self.local_selectors))
        remote_match = any(destination_ip in network and proto == protocol and ports is not None and ports[0] <= port <= ports[1] for network, proto, ports in map(self._parse_selector, self.remote_selectors))
        return local_match and remote_match

    def get_connection_name(self) -> str:
        """Return the captured connection name.

        Returns:
            str: Captured association identity.
        """
        return self.connection_name

    def get_local_host(self) -> str:
        """Return the captured local host.

        Returns:
            str: Captured association identity.
        """
        return self.local_host

    def get_remote_host(self) -> str:
        """Return the captured remote host.

        Returns:
            str: Captured association identity.
        """
        return self.remote_host

    def get_name(self) -> str:
        """Return the captured name.

        Returns:
            str: Captured association identity.
        """
        return self.name

    def get_unique_id(self) -> str:
        """Return the captured unique id.

        Returns:
            str: Captured association identity.
        """
        return self.unique_id

    def get_local_selectors(self) -> list[str]:
        """Return the captured local selectors.

        Returns:
            list[str]: Captured association identity.
        """
        return list(self.local_selectors)

    def get_remote_selectors(self) -> list[str]:
        """Return the captured remote selectors.

        Returns:
            list[str]: Captured association identity.
        """
        return list(self.remote_selectors)
