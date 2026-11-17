"""Pod JSON evidence for placement, addresses and runtime images."""

import copy
import ipaddress
import json


class PodJsonOutput:
    """Preserve a pod snapshot independently of the caller."""

    def __init__(self, content: str | dict):
        """Parse a command response or a pod from a workload snapshot.

        Args:
            content (str | dict): Pod JSON or decoded pod record.
        """
        self.pod = json.loads(content) if isinstance(content, str) else copy.deepcopy(content)

    def get_uid(self) -> str:
        """Return the pod identity.

        Returns:
            str: Pod UID.
        """
        return self.pod["metadata"]["uid"]

    def get_node_name(self) -> str | None:
        """Return the scheduled node.

        Returns:
            str | None: Node name or unscheduled state.
        """
        return self.pod["spec"].get("nodeName")

    def get_pod_ips(self, family: int | None = None) -> list[str]:
        """Return observed pod addresses, optionally filtered by IP family.

        Args:
            family (int | None): IP version or all versions.

        Returns:
            list[str]: Published pod addresses.
        """
        addresses = [item["ip"] for item in self.pod.get("status", {}).get("podIPs", [])]
        return [address for address in addresses if family is None or ipaddress.ip_address(address).version == family]

    def get_container_digests(self) -> dict[str, str]:
        """Normalize runtime image identities for the observed containers.

        Returns:
            dict[str, str]: Container names mapped to digests.
        """
        return {item["name"]: item.get("imageID", "").split("@")[-1].removeprefix("containerd://").removeprefix("docker://") for item in self.pod["status"]["containerStatuses"]}
