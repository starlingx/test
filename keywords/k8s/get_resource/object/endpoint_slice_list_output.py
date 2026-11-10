"""EndpointSlice identity and ready-address interpretation."""

import ipaddress
import json

from framework.exceptions.keyword_exception import KeywordException
from keywords.k8s.pods.object.pod_json_output import PodJsonOutput


class EndpointSliceListOutput:
    """Parse service endpoints independently of command execution and polling."""

    def __init__(self, content: str):
        """Parse an EndpointSlice list.

        Args:
            content (str): EndpointSlice list JSON.
        """
        self.slices = json.loads(content)["items"]

    def get_ready_endpoint_address(self, service_name: str, server: PodJsonOutput, port: int, protocol: str, family: int) -> str | None:
        """Resolve a unique ready address against independent pod evidence.

        Args:
            service_name (str): Expected service label.
            server (PodJsonOutput): Independently observed server pod.
            port (int): Expected service port.
            protocol (str): TCP or UDP protocol name.
            family (int): Requested IP version.

        Returns:
            str | None: Verified address or pending publication.
        """
        addresses = []
        for endpoint_slice in self.slices:
            if endpoint_slice["metadata"].get("labels", {}).get("kubernetes.io/service-name") != service_name:
                continue
            if not any(published_port.get("port") == port and published_port.get("protocol") == protocol.upper() for published_port in endpoint_slice.get("ports", [])):
                raise KeywordException("EndpointSlice published the wrong protocol or port")
            for endpoint in endpoint_slice.get("endpoints", []):
                if endpoint.get("conditions", {}).get("ready") is not True or endpoint.get("conditions", {}).get("terminating"):
                    continue
                target = endpoint.get("targetRef", {})
                if target.get("uid") != server.get_uid() or endpoint.get("nodeName") != server.get_node_name():
                    raise KeywordException("EndpointSlice points to an unexpected peer")
                addresses.extend(address for address in endpoint["addresses"] if ipaddress.ip_address(address).version == family)
        pod_addresses = set(server.get_pod_ips())
        if len(addresses) > 1 or any(address not in pod_addresses for address in addresses):
            raise KeywordException("Ambiguous or inconsistent endpoint identity")
        return addresses[0] if addresses else None
