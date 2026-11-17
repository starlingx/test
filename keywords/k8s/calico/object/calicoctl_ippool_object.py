"""Object for a single IP pool from 'calicoctl get ippool'."""


class CalicoctlIppoolObject:
    """One IPPool from 'calicoctl get ippool -o yaml'."""

    def __init__(self, ippool_dict: dict):
        """Initialize from a parsed IPPool document.

        Args:
            ippool_dict (dict): A single parsed IPPool YAML document.
        """
        self.metadata = ippool_dict.get("metadata", {}) or {}
        self.spec = ippool_dict.get("spec", {}) or {}

    def get_name(self) -> str:
        """Get the IP pool name.

        Returns:
            str: The metadata.name of the IP pool.
        """
        return self.metadata.get("name", "")

    def get_cidr(self) -> str:
        """Get the IP pool CIDR.

        Returns:
            str: The spec.cidr of the IP pool.
        """
        return self.spec.get("cidr", "")

    def get_nat_outgoing(self) -> bool:
        """Get whether NAT outgoing is enabled.

        calicoctl omits natOutgoing from its output when it is false, so a missing
        value is reported as False (the calicoctl default).

        Returns:
            bool: True if NAT outgoing is enabled, False otherwise.
        """
        return bool(self.spec.get("natOutgoing", False))

    def __str__(self) -> str:
        """Human-readable representation of the IP pool.

        Returns:
            str: The IP pool name and CIDR.
        """
        return f"CalicoctlIppoolObject(name={self.get_name()}, cidr={self.get_cidr()})"
