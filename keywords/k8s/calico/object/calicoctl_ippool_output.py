"""Output object for 'calicoctl get ippool -o yaml'."""

import yaml

from keywords.k8s.calico.object.calicoctl_ippool_object import CalicoctlIppoolObject


class CalicoctlIppoolOutput:
    """Parsed output from 'calicoctl get ippool -o yaml'.

    calicoctl returns either a single IPPool document or a List document
    containing several IPPool items. This object normalises both into a list
    of CalicoctlIppoolObject, so keywords and test cases never parse the raw
    YAML or index dictionaries themselves.
    """

    def __init__(self, raw_output: str | list[str]):
        """Parse the raw IP pool YAML output.

        Handles both the single-document and list forms: 'calicoctl get ippool -o yaml'
        returns an IPPoolList, while 'kubectl get ippools -o yaml' wraps the pools in a
        generic List (kind: List). Any document carrying an 'items' list is treated as a
        list of pools; a bare document with kind IPPool is treated as a single pool.

        Args:
            raw_output (str | list[str]): Raw SSH command output.
        """
        content = "".join(raw_output) if isinstance(raw_output, list) else raw_output
        parsed = yaml.safe_load(content) if content and content.strip() else {}

        raw_pools: list = []
        if isinstance(parsed, dict) and isinstance(parsed.get("items"), list):
            raw_pools = [item for item in parsed["items"] if isinstance(item, dict) and item.get("kind") == "IPPool"]
        elif isinstance(parsed, dict) and parsed.get("kind") == "IPPool":
            raw_pools = [parsed]
        self.ippools: list[CalicoctlIppoolObject] = [CalicoctlIppoolObject(pool) for pool in raw_pools]

    def get_ippools(self) -> list[CalicoctlIppoolObject]:
        """Get all IP pool objects.

        Returns:
            list[CalicoctlIppoolObject]: All parsed IP pool entries.
        """
        return self.ippools

    def get_ippool_by_name(self, pool_name: str) -> CalicoctlIppoolObject:
        """Get a single IP pool by name.

        Args:
            pool_name (str): The metadata.name of the IP pool.

        Returns:
            CalicoctlIppoolObject: The matching IP pool.

        Raises:
            ValueError: If no IP pool with the given name exists.
        """
        for pool in self.ippools:
            if pool.get_name() == pool_name:
                return pool
        raise ValueError(f"No IP pool found with name '{pool_name}'.")

    def is_empty(self) -> bool:
        """Check whether any IP pools were parsed.

        Returns:
            bool: True if there are no IP pools, False otherwise.
        """
        return len(self.ippools) == 0

    def has_ippool_with_cidr(self, cidr: str) -> bool:
        """Check whether any IP pool has the given CIDR.

        Args:
            cidr (str): The CIDR to look for (e.g. '192.168.200.0/24').

        Returns:
            bool: True if an IP pool with the given CIDR exists, False otherwise.
        """
        return any(pool.get_cidr() == cidr for pool in self.ippools)

    def __str__(self) -> str:
        """Human-readable representation of the parsed IP pools.

        Returns:
            str: Summary listing the IP pool names.
        """
        return f"CalicoctlIppoolOutput(ippools={[pool.get_name() for pool in self.ippools]})"
