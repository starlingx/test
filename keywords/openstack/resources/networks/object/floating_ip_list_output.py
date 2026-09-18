"""Parses and provides access to a collection of FloatingIpObjects."""

from typing import Dict, List, Optional

from keywords.openstack.resources.networks.object.floating_ip_object import FloatingIpObject


class FloatingIpListOutput:
    """Parses and provides access to a collection of FloatingIpObjects."""

    def __init__(self, raw_floating_ips: List[Dict]) -> None:
        """Initialize FloatingIpListOutput from raw floating-IP dicts.

        Args:
            raw_floating_ips (List[Dict]): Raw floating-IP dicts from the
                openstacksdk Network resource.
        """
        self._floating_ips: List[FloatingIpObject] = []
        for raw in raw_floating_ips:
            floating_ip = FloatingIpObject()
            floating_ip.set_id(raw.get("id", ""))
            floating_ip.set_floating_ip_address(raw.get("floating_ip_address", ""))
            floating_ip.set_status(raw.get("status", ""))
            floating_ip.set_port_id(raw.get("port_id", "") or "")
            floating_ip.set_floating_network_id(raw.get("floating_network_id", ""))
            self._floating_ips.append(floating_ip)

    def get_floating_ips(self) -> List[FloatingIpObject]:
        """Get all parsed floating-IP objects.

        Returns:
            List[FloatingIpObject]: All floating IPs in this output.
        """
        return self._floating_ips

    def get_floating_ip_by_id(self, floating_ip_id: str) -> Optional[FloatingIpObject]:
        """Get a floating IP by ID.

        Args:
            floating_ip_id (str): Floating IP UUID.

        Returns:
            Optional[FloatingIpObject]: Matching floating IP, or None.
        """
        for floating_ip in self._floating_ips:
            if floating_ip.get_id() == floating_ip_id:
                return floating_ip
        return None

    def __object_to_string__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"FloatingIpListOutput(count={len(self._floating_ips)})"
