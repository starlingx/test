import re
from typing import Dict


class KubectlClusterroleDescriptionOutput:
    """Parsed output of 'kubectl describe clusterrole <name>'."""

    def __init__(self, raw_output: str):
        """Constructor.

        Args:
            raw_output (str): Raw string output from 'kubectl describe clusterrole'.
        """
        self.raw_output = raw_output
        self.resource_verbs: Dict[str, str] = {}
        self._parse()

    def _parse(self):
        """Parse the PolicyRule section to extract resource -> verbs mapping."""
        in_policy_section = False
        for line in self.raw_output.splitlines():
            stripped = line.strip()
            if stripped.startswith("PolicyRule:"):
                in_policy_section = True
                continue
            if stripped.startswith("Resources") or stripped.startswith("---------"):
                continue
            if in_policy_section and stripped:
                # Match: resource  []  []  [verbs]
                match = re.match(r"(\S+)\s+\[.*?\]\s+\[.*?\]\s+(\[.*?\])", stripped)
                if match:
                    resource = match.group(1)
                    verbs = match.group(2)
                    self.resource_verbs[resource] = verbs

    def get_resource_verbs(self) -> Dict[str, str]:
        """
        Get the mapping of resources to their verbs.

        Returns:
            Dict[str, str]: resource name -> verbs string (e.g. '[get list watch]')
        """
        return self.resource_verbs

    def has_resource_with_verbs(self, resource: str, expected_verbs: str) -> bool:
        """Check if a resource exists with the expected verbs.

        Args:
            resource (str): The resource name to check.
            expected_verbs (str): The expected verbs string (e.g. '[get list watch]').

        Returns:
            bool: True if the resource has the expected verbs.
        """
        actual_verbs = self.resource_verbs.get(resource.strip())
        return actual_verbs == expected_verbs if actual_verbs else False
