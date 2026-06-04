"""Security group object representing a Neutron security group."""

from typing import List


class SecurityGroupObject:
    """Represents a single Neutron security group."""

    def __init__(self) -> None:
        """Initialize SecurityGroupObject with empty values."""
        self.id: str = ""
        self.name: str = ""
        self.rules: List[dict] = []

    def get_id(self) -> str:
        """Get security group ID.

        Returns:
            str: Security group UUID.
        """
        return self.id

    def set_id(self, value: str) -> None:
        """Set security group ID.

        Args:
            value (str): Security group UUID.
        """
        self.id = value

    def get_name(self) -> str:
        """Get security group name.

        Returns:
            str: Security group name.
        """
        return self.name

    def set_name(self, value: str) -> None:
        """Set security group name.

        Args:
            value (str): Security group name.
        """
        self.name = value

    def get_rules(self) -> List[dict]:
        """Get security group rules.

        Returns:
            List[dict]: List of rule dicts.
        """
        return self.rules

    def set_rules(self, rules: List[dict]) -> None:
        """Set security group rules.

        Args:
            rules (List[dict]): List of rule dicts.
        """
        self.rules = rules

    def has_allow_all_ingress_rule(self) -> bool:
        """Check if this security group has an allow-all ingress rule.

        Returns:
            bool: True if allow-all ingress rule exists.
        """
        for rule in self.rules:
            if (rule.get("direction") == "ingress" and
                    rule.get("protocol") is None and
                    rule.get("remote_ip_prefix") in (None, "0.0.0.0/0")):
                return True
        return False

    def __str__(self) -> str:
        """Human-readable summary.

        Returns:
            str: Summary string.
        """
        return f"SecurityGroupObject(id={self.id}, name={self.name}, rules={len(self.rules)})"
