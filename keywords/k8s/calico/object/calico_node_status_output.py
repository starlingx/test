"""Output object for 'calico-node -show-status'."""

import re

from keywords.cloud_platform.system.system_table_parser import SystemTableParser
from keywords.k8s.calico.object.calico_node_bgp_peer_object import CalicoNodeBgpPeerObject

# Section titles printed before each table, e.g. 'bird v4 status' or 'bird v6 BGP peers'.
_SECTION_TITLE = re.compile(r"^bird (v4|v6) (status|BGP peers|routes)$")


class CalicoNodeStatusOutput:
    """Parsed output of 'calico-node -show-status'.

    The output has one block per bird instance (v4 and/or v6), each made of titled tables:
    'bird vX status' (READY, VERSION, ...), 'bird vX BGP peers' (PEER ADDRESS, ..., BGPSTATE)
    and 'bird vX routes'. Each table is parsed with the framework SystemTableParser.
    """

    def __init__(self, raw_output: str | list[str]):
        """Parse the raw calico-node status output.

        Args:
            raw_output (str | list[str]): Raw SSH command output.
        """
        content = "".join(raw_output) if isinstance(raw_output, list) else str(raw_output)
        sections = self._split_sections(content.splitlines())

        self.bird_ready: dict[str, bool] = {}
        self.bgp_peers_sections: list[str] = []
        self.bgp_peers: list[CalicoNodeBgpPeerObject] = []

        for (ip_version, table_name), lines in sections.items():
            rows = SystemTableParser([f"{line}\n" for line in lines]).get_output_values_list()
            if table_name == "status":
                self.bird_ready[ip_version] = bool(rows) and rows[0].get("READY") == "true"
            elif table_name == "BGP peers":
                self.bgp_peers_sections.append(ip_version)
                for row in rows:
                    peer = CalicoNodeBgpPeerObject(ip_version, row.get("PEER ADDRESS", ""))
                    peer.set_peer_type(row.get("PEER TYPE", ""))
                    peer.set_state(row.get("STATE", ""))
                    peer.set_bgp_state(row.get("BGPSTATE", ""))
                    self.bgp_peers.append(peer)

    @staticmethod
    def _split_sections(lines: list[str]) -> dict[tuple[str, str], list[str]]:
        """Group the table lines of the output under their section title.

        Args:
            lines (list[str]): The output lines.

        Returns:
            dict[tuple[str, str], list[str]]: Mapping of (ip_version, table_name) to that section's table lines.
        """
        sections = {}
        current = None
        for line in lines:
            match = _SECTION_TITLE.match(line.strip())
            if match:
                current = (match.group(1), match.group(2))
                sections[current] = []
            elif current and line.strip().startswith(("+", "|")):
                sections[current].append(line.strip())
        return sections

    def get_ip_versions(self) -> list[str]:
        """Get the bird instances that reported a status table.

        Returns:
            list[str]: The IP versions present, e.g. ['v4'] or ['v4', 'v6'].
        """
        return sorted(self.bird_ready.keys())

    def is_bird_ready(self, ip_version: str) -> bool:
        """Check whether a bird instance reports READY=true.

        Args:
            ip_version (str): 'v4' or 'v6'.

        Returns:
            bool: True if that bird instance is present and ready.
        """
        return self.bird_ready.get(ip_version, False)

    def has_bgp_peers_section(self, ip_version: str) -> bool:
        """Check whether a bird instance printed its BGP peers table.

        Args:
            ip_version (str): 'v4' or 'v6'.

        Returns:
            bool: True if the 'bird <ip_version> BGP peers' table is present.
        """
        return ip_version in self.bgp_peers_sections

    def get_bgp_peers(self) -> list[CalicoNodeBgpPeerObject]:
        """Get the BGP peers of every bird instance.

        Returns:
            list[CalicoNodeBgpPeerObject]: All parsed BGP peers.
        """
        return self.bgp_peers

    def get_bgp_peers_not_established(self) -> list[str]:
        """Get the BGP peers whose session is not Established.

        Returns:
            list[str]: Human-readable descriptions of the peers that are not Established.
        """
        return [str(peer) for peer in self.bgp_peers if not peer.is_established()]

    def __str__(self) -> str:
        """Human-readable representation of the parsed status.

        Returns:
            str: The bird readiness per IP version and the BGP peers.
        """
        return f"CalicoNodeStatusOutput(bird_ready={self.bird_ready}, bgp_peers={[str(peer) for peer in self.bgp_peers]})"
