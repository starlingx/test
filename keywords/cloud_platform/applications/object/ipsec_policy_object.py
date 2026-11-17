"""Typed IPsec application evidence."""

import copy


class IPsecPolicyObject:
    """Identity and desired spec of a cluster-scoped policy."""

    def __init__(self, resource: dict):
        """Capture policy identity.

        Args:
            resource (dict): Kubernetes policy resource.
        """
        self.name = resource["metadata"]["name"]
        self.uid = resource["metadata"]["uid"]
        self.spec = copy.deepcopy(resource["spec"])

    def get_name(self) -> str:
        """Return the policy name.

        Returns:
            str: Resource name.
        """
        return self.name

    def get_uid(self) -> str:
        """Return the original resource UID.

        Returns:
            str: Kubernetes UID.
        """
        return self.uid

    def get_spec(self) -> dict:
        """Return an isolated copy of the desired policy specification.

        Returns:
            dict: Kubernetes API policy spec.
        """
        return copy.deepcopy(self.spec)
