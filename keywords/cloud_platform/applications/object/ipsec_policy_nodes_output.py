"""Typed IPsec application evidence."""

import ipaddress
import json

from framework.exceptions.keyword_exception import KeywordException


class IPsecPolicyNodesOutput:
    """Cross-check Kubernetes addresses and health against platform inventory."""

    def __init__(self, content: str, eligible: set[str], hosts: dict, family: int):
        """Parse independently eligible nodes.

        Args:
            content (str): Complete Kubernetes node list JSON.
            eligible (set[str]): Rendered scheduling's node names.
            hosts (dict): Platform host objects indexed by name.
            family (int): Configured IP family.
        """
        nodes = json.loads(content)["items"]
        addresses = {}
        for node in nodes:
            name = node["metadata"]["name"]
            if name not in eligible:
                continue
            if name not in hosts:
                raise KeywordException(f"Agent node {name} is missing from platform inventory")
            host = hosts[name]
            if host.get_personality() == "storage":
                raise KeywordException(f"Storage node {name} is incorrectly eligible for the policy agent")
            if (host.get_administrative(), host.get_operational(), host.get_availability()) != ("unlocked", "enabled", "available"):
                raise KeywordException(f"Policy node {name} is not healthy in platform inventory")
            if not any(condition.get("type") == "Ready" and condition.get("status") == "True" for condition in node.get("status", {}).get("conditions", [])):
                raise KeywordException(f"Policy node {name} is not Ready")
            candidates = [str(ipaddress.ip_address(item["address"])) for item in node["status"].get("addresses", []) if item["type"] == "InternalIP" and ipaddress.ip_address(item["address"]).version == family]
            if len(candidates) != 1:
                raise KeywordException(f"Expected one IPv{family} InternalIP for {name}")
            addresses[name] = candidates[0]
        if len(addresses) < 2 or len(set(addresses.values())) != len(addresses):
            raise KeywordException("Policy traffic requires two distinct ready non-storage nodes and unique addresses")
        self.addresses = addresses

    def get_node_names(self) -> tuple[str, ...]:
        """Return selected node names.

        Returns:
            tuple[str, ...]: Eligible node identities.
        """
        return tuple(self.addresses)

    def get_address(self, node: str) -> str:
        """Return an independently discovered cluster-host IP.

        Args:
            node (str): Node identity.

        Returns:
            str: Cluster-host address.
        """
        return self.addresses[node]
