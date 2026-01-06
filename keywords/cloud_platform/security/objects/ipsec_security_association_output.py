import re
from typing import Union

from keywords.cloud_platform.security.objects.ipsec_security_association_object import IPSecSecurityAssociationObject


class IPSecSecurityAssociationOutput:
    """Parser for swanctl --list-sa command output."""

    def __init__(self, command_output: Union[str, list[str]]):
        """Initialize the parser with command output.

        Args:
            command_output (Union[str, list[str]]): Output from swanctl --list-sa command.
        """
        if command_output is None:
            self.raw_output = ""
        elif isinstance(command_output, list):
            self.raw_output = "\n".join(command_output) if command_output else ""
        else:
            self.raw_output = command_output

        if not self.raw_output.strip():
            self.associations = []
            return

        self.associations = self.parse_associations()

    def parse_associations(self) -> list[IPSecSecurityAssociationObject]:
        """Parse the security associations from the command output.

        Returns:
            list[IPSecSecurityAssociationObject]: List of parsed security associations.
        """
        associations = []
        pattern = re.compile(r"(system-nodes:.*?)(?=system-nodes:|\Z)", re.DOTALL)
        matches = pattern.findall(self.raw_output)

        for i, match in enumerate(matches):
            if match.strip():  # Only create association if match has content
                association = IPSecSecurityAssociationObject(f"system-nodes-{i+1}", match.strip())
                associations.append(association)

        return associations

    def get_associations(self) -> list[IPSecSecurityAssociationObject]:
        """Get all security associations.

        Returns:
            list[IPSecSecurityAssociationObject]: List of security associations.
        """
        return self.associations
