"""Correlated policy tunnel and traffic evidence."""

import copy

from keywords.cloud_platform.applications.object.ipsec_policy_traffic_output import IPsecPolicyTrafficOutput


class IPsecPolicyTrafficEvidence:
    """Capture a fresh response and counters for matched policy CHILD_SAs."""

    def __init__(self, traffic: IPsecPolicyTrafficOutput, associations: list, before: dict, after: dict):
        """Capture one flow observation.

        Args:
            traffic (IPsecPolicyTrafficOutput): Checked fresh response.
            associations (list): Matching CHILD_SA identities with progress.
            before (dict): Original counters indexed by association identity.
            after (dict): Fresh counters indexed by association identity.
        """
        self.traffic = traffic
        self.associations = list(associations)
        self.before = copy.deepcopy(before)
        self.after = copy.deepcopy(after)

    def get_traffic(self) -> IPsecPolicyTrafficOutput:
        """Return validated traffic.

        Returns:
            IPsecPolicyTrafficOutput: Fresh response evidence.
        """
        return self.traffic

    def get_associations(self) -> list:
        """Return matched association identities.

        Returns:
            list: CHILD_SA identities with increasing counters.
        """
        return list(self.associations)

    def get_before_counters(self) -> dict:
        """Return baseline counters.

        Returns:
            dict: Counter snapshot by association identity.
        """
        return copy.deepcopy(self.before)

    def get_after_counters(self) -> dict:
        """Return fresh counters.

        Returns:
            dict: Counter snapshot by association identity.
        """
        return copy.deepcopy(self.after)
