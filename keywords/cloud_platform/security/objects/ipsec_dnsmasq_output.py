from typing import Union

from keywords.cloud_platform.security.objects.ipsec_dnsmasq_object import IPSecDnsmasqObject


class IPSecDnsmasqOutput:
    """Parser for dnsmasq.hosts file content."""

    def __init__(self, dnsmasq_content: Union[str, list[str]]):
        """Initialize dnsmasq output parser.

        Args:
            dnsmasq_content (Union[str, list[str]]): Raw dnsmasq.hosts content.
        """
        self.content = "\n".join(dnsmasq_content) if isinstance(dnsmasq_content, list) else dnsmasq_content
        self.entries = self._parse_entries()

    def _parse_entries(self) -> list[IPSecDnsmasqObject]:
        """Parse dnsmasq entries from content.

        Returns:
            list[IPSecDnsmasqObject]: List of parsed dnsmasq entries.
        """
        if not self.content.strip():
            return []

        entries = []
        for line in self.content.strip().split("\n"):
            if not line.strip():
                continue

            parts = line.split(",")
            if len(parts) >= 3:
                mac = parts[0].strip()
                name = parts[1].strip()
                address = parts[2].strip()
                if mac and name and address:
                    entries.append(IPSecDnsmasqObject(mac, name, address))

        return entries

    def get_entries(self) -> list[IPSecDnsmasqObject]:
        """Get all dnsmasq entries.

        Returns:
            list[IPSecDnsmasqObject]: List of dnsmasq entries.
        """
        return self.entries

    def get_content(self) -> str:
        """Get raw dnsmasq content.

        Returns:
            str: Raw dnsmasq.hosts content.
        """
        return self.content

    def get_pxeboot_entries(self) -> list[IPSecDnsmasqObject]:
        """Get only pxeboot entries.

        Returns:
            list[IPSecDnsmasqObject]: List of pxeboot dnsmasq entries.
        """
        return [entry for entry in self.entries if entry.is_pxeboot_entry()]
