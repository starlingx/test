"""Output object for 'kubectl get installation default -o yaml'."""

import json
from typing import Optional

import yaml

from keywords.k8s.calico.object.installation_ip_pool_object import InstallationIPPoolObject


class InstallationOutput:
    """Parsed output from 'kubectl get installation default -o yaml'."""

    def __init__(self, raw_output: str | list[str]):
        """Parse the raw Installation CR YAML output.

        Args:
            raw_output (str | list[str]): Raw SSH command output.
        """
        content = "".join(raw_output) if isinstance(raw_output, list) else raw_output
        data = yaml.safe_load(content) or {}
        self.spec = data.get("spec") or {}
        self.calico_network = self.spec.get("calicoNetwork") or {}
        self.ip_pools_spec: list[dict] = self.calico_network.get("ipPools") or []
        self.ip_pools: list[InstallationIPPoolObject] = [self.build_ip_pool_object_from_dict(pool) for pool in self.ip_pools_spec]

    @staticmethod
    def build_ip_pool_object_from_dict(pool_dict: dict) -> InstallationIPPoolObject:
        """Build an IP pool object from one spec.calicoNetwork.ipPools entry.

        Args:
            pool_dict (dict): One parsed ipPools entry.

        Returns:
            InstallationIPPoolObject: The IP pool.

        Raises:
            ValueError: If the entry has no CIDR.
        """
        cidr = pool_dict.get("cidr")
        if not cidr:
            raise ValueError(f"Installation ipPools entry has no cidr: {pool_dict}")
        return InstallationIPPoolObject(
            pool_dict.get("name"),
            cidr,
            pool_dict.get("blockSize"),
            pool_dict.get("encapsulation"),
            pool_dict.get("natOutgoing"),
            pool_dict.get("nodeSelector"),
        )

    def get_registry(self) -> Optional[str]:
        """Get the image registry the operator pulls Calico images from.

        Returns:
            Optional[str]: The spec.registry value, or None when it is not set.
        """
        return self.spec.get("registry")

    def get_mtu(self) -> Optional[int]:
        """Get the custom MTU.

        Returns:
            Optional[int]: The spec.calicoNetwork.mtu value, or None when no custom MTU is set.
        """
        return self.calico_network.get("mtu")

    def get_image_pull_secret_names(self) -> list[str]:
        """Get the names of the image pull secrets the operator uses.

        Returns:
            list[str]: The spec.imagePullSecrets names; empty when none are configured.
        """
        return [secret.get("name") for secret in self.spec.get("imagePullSecrets") or [] if secret.get("name")]

    def get_ip_pools(self) -> list[InstallationIPPoolObject]:
        """Get the IP pools.

        Returns:
            list[InstallationIPPoolObject]: The spec.calicoNetwork.ipPools entries.
        """
        return self.ip_pools

    def get_ip_pool_cidrs(self) -> list[str]:
        """Get the CIDRs of all IP pools.

        Returns:
            list[str]: One CIDR per IP pool.
        """
        return [pool.get_cidr() for pool in self.ip_pools]

    def has_ip_pool_with_ip_version(self, ip_version: int) -> bool:
        """Check whether an IP pool of the given IP version exists.

        Args:
            ip_version (int): 4 or 6.

        Returns:
            bool: True if an IP pool of that version exists, False otherwise.
        """
        return any(pool.get_ip_version() == ip_version for pool in self.ip_pools)

    def get_ip_pool_by_ip_version(self, ip_version: int) -> InstallationIPPoolObject:
        """Get the IP pool of the given IP version.

        Args:
            ip_version (int): 4 or 6.

        Returns:
            InstallationIPPoolObject: The first IP pool of that version.

        Raises:
            ValueError: If no IP pool of that version exists.
        """
        for pool in self.ip_pools:
            if pool.get_ip_version() == ip_version:
                return pool
        raise ValueError(f"Installation CR has no IPv{ip_version} pool; pools: {self.get_ip_pool_cidrs()}")

    def get_ip_family(self) -> str:
        """Get the IP family of the cluster from its IP pools.

        Returns:
            str: 'ipv4', 'ipv6' or 'dual'.

        Raises:
            ValueError: If the Installation CR has no IP pool.
        """
        has_ipv4 = self.has_ip_pool_with_ip_version(4)
        has_ipv6 = self.has_ip_pool_with_ip_version(6)
        if has_ipv4 and has_ipv6:
            return "dual"
        if has_ipv6:
            return "ipv6"
        if has_ipv4:
            return "ipv4"
        raise ValueError("Installation CR has no IP pool")

    def get_ip_pools_json(self) -> str:
        """Get the IP pools exactly as configured, serialized as JSON.

        Used to restore the original pools after a test changes them, so every field is
        restored, including fields this object has no getter for.

        Returns:
            str: The spec.calicoNetwork.ipPools list as a JSON string.
        """
        return json.dumps(self.ip_pools_spec)

    def get_ip_pools_json_with_cidr_replaced(self, current_cidr: str, new_cidr: str) -> str:
        """Get the IP pools as JSON with the CIDR of one pool replaced.

        Every other field and every other pool is kept, so only the CIDR changes.

        Args:
            current_cidr (str): The CIDR of the pool to change.
            new_cidr (str): The CIDR to set on that pool.

        Returns:
            str: The spec.calicoNetwork.ipPools list as a JSON string.

        Raises:
            ValueError: If no pool has the current CIDR.
        """
        if current_cidr not in self.get_ip_pool_cidrs():
            raise ValueError(f"Installation CR has no IP pool with CIDR {current_cidr}; pools: {self.get_ip_pool_cidrs()}")
        return json.dumps([{**pool, "cidr": new_cidr} if pool.get("cidr") == current_cidr else pool for pool in self.ip_pools_spec])

    def get_ip_pools_json_with_added_pool(self, pool_name: str, cidr: str) -> str:
        """Get the IP pools as JSON with one more pool appended.

        The new pool copies the settings of the first pool, with its own name and CIDR.

        Args:
            pool_name (str): The name of the new pool.
            cidr (str): The CIDR of the new pool.

        Returns:
            str: The spec.calicoNetwork.ipPools list as a JSON string.

        Raises:
            ValueError: If the Installation CR has no IP pool to copy the settings from.
        """
        if not self.ip_pools_spec:
            raise ValueError("Installation CR has no IP pool to copy the settings from")
        new_pool = {key: value for key, value in self.ip_pools_spec[0].items() if key != "blockSize"}
        new_pool.update({"name": pool_name, "cidr": cidr})
        return json.dumps([*self.ip_pools_spec, new_pool])

    def __str__(self) -> str:
        """Human-readable representation of the Installation CR.

        Returns:
            str: Summary of the registry, IP pools and MTU.
        """
        return f"InstallationOutput(registry={self.get_registry()}, ip_pools={self.get_ip_pool_cidrs()}, mtu={self.get_mtu()})"
