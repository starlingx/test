"""Typed IPsec application evidence."""

import json

from keywords.cloud_platform.applications.object.ipsec_policy_object import IPsecPolicyObject


class IPsecPolicyListOutput:
    """Parse a checked Kubernetes policy list."""

    def __init__(self, content: str):
        """Parse policy records.

        Args:
            content (str): JSON list response.
        """
        self.policies = [IPsecPolicyObject(item) for item in json.loads(content)["items"]]

    def get_policies(self) -> list[IPsecPolicyObject]:
        """Return captured policy objects.

        Returns:
            list[IPsecPolicyObject]: Policy records.
        """
        return list(self.policies)
