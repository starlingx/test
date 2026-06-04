"""Security group output — collection of SecurityGroupObjects."""

from typing import List, Optional

from keywords.openstack.resources.security_groups.object.security_group_object import SecurityGroupObject


class SecurityGroupOutput:
    """Parsed output from security group list operations."""

    def __init__(self, security_groups: List[SecurityGroupObject]) -> None:
        """Initialize SecurityGroupOutput.

        Args:
            security_groups (List[SecurityGroupObject]): List of security group objects.
        """
        self._security_groups = security_groups

    def get_security_groups(self) -> List[SecurityGroupObject]:
        """Get all security groups.

        Returns:
            List[SecurityGroupObject]: List of security group objects.
        """
        return self._security_groups

    def find_by_name(self, name: str) -> Optional[SecurityGroupObject]:
        """Find a security group by name.

        Args:
            name (str): Security group name.

        Returns:
            Optional[SecurityGroupObject]: Security group or None.
        """
        for sg in self._security_groups:
            if sg.get_name() == name:
                return sg
        return None

    def __str__(self) -> str:
        """Human-readable summary.

        Returns:
            str: Summary string.
        """
        return f"SecurityGroupOutput(count={len(self._security_groups)})"
