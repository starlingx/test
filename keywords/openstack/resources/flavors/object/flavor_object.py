"""Flavor object representation."""

from typing import Dict


class FlavorObject:
    """Represents a single OpenStack flavor."""

    def __init__(self) -> None:
        """Initialize an empty FlavorObject."""
        self.id = ""
        self.name = ""
        self.ram = 0
        self.vcpus = 0
        self.disk = 0
        self.extra_specs = {}

    def get_id(self) -> str:
        """Get the flavor ID.

        Returns:
            str: Flavor ID.
        """
        return self.id

    def set_id(self, flavor_id: str) -> None:
        """Set the flavor ID.

        Args:
            flavor_id (str): Flavor ID.
        """
        self.id = flavor_id

    def get_name(self) -> str:
        """Get the flavor name.

        Returns:
            str: Flavor name.
        """
        return self.name

    def set_name(self, name: str) -> None:
        """Set the flavor name.

        Args:
            name (str): Flavor name.
        """
        self.name = name

    def get_ram(self) -> int:
        """Get the RAM in MB.

        Returns:
            int: RAM in MB.
        """
        return self.ram

    def set_ram(self, ram: int) -> None:
        """Set the RAM in MB.

        Args:
            ram (int): RAM in MB.
        """
        self.ram = ram

    def get_vcpus(self) -> int:
        """Get the number of vCPUs.

        Returns:
            int: Number of vCPUs.
        """
        return self.vcpus

    def set_vcpus(self, vcpus: int) -> None:
        """Set the number of vCPUs.

        Args:
            vcpus (int): Number of vCPUs.
        """
        self.vcpus = vcpus

    def get_disk(self) -> int:
        """Get the disk size in GB.

        Returns:
            int: Disk size in GB.
        """
        return self.disk

    def set_disk(self, disk: int) -> None:
        """Set the disk size in GB.

        Args:
            disk (int): Disk size in GB.
        """
        self.disk = disk

    def get_extra_specs(self) -> Dict[str, str]:
        """Get the flavor extra specs.

        Extra specs carry the scheduling-relevant properties of a flavor, such
        as ``hw:mem_page_size`` (huge-page backing) and ``hw:cpu_policy`` (CPU
        pinning). They are the properties that actually decide whether an
        instance can be scheduled on a given lab, so capability-aware flavor
        selection reads them rather than inferring from the flavor name.

        Returns:
            Dict[str, str]: Extra spec key-value pairs (empty if the flavor has none).
        """
        return self.extra_specs

    def set_extra_specs(self, extra_specs: Dict[str, str]) -> None:
        """Set the flavor extra specs.

        Args:
            extra_specs (Dict[str, str]): Extra spec key-value pairs.
        """
        self.extra_specs = extra_specs if extra_specs else {}

    def get_memory_page_size(self) -> str:
        """Get the ``hw:mem_page_size`` extra spec.

        Returns:
            str: The configured memory page size (e.g. ``large`` or ``1048576``),
                or an empty string if the flavor does not set one.
        """
        return self.get_extra_specs().get("hw:mem_page_size", "")

    def is_huge_page_backed(self) -> bool:
        """Check whether the flavor requests huge-page backing.

        A huge-page-backed flavor is required to boot on OVS-DPDK labs, whose
        tenant networks use vhostuser interfaces that need shared-memory guests.

        Returns:
            bool: True if ``hw:mem_page_size`` is set to a non-empty value.
        """
        return self.get_memory_page_size() != ""

    def get_cpu_policy(self) -> str:
        """Get the ``hw:cpu_policy`` extra spec.

        Returns:
            str: ``dedicated``, ``shared``, or an empty string when the flavor
                does not pin CPUs (Nova treats the absence as shared).
        """
        return self.get_extra_specs().get("hw:cpu_policy", "")

    def is_dedicated_cpu(self) -> bool:
        """Check whether the flavor pins CPUs (dedicated policy).

        Dedicated-CPU flavors are the ones that trigger same-host resize CPU
        unpinning errors on PCPU-constrained single-host labs, so resize tests
        need the boot and target flavors to share the same CPU policy.

        Returns:
            bool: True if ``hw:cpu_policy`` is ``dedicated``.
        """
        return self.get_cpu_policy() == "dedicated"

    def get_effective_cpu_policy(self) -> str:
        """Get the CPU policy, normalizing the absent case to ``shared``.

        Nova treats a flavor with no ``hw:cpu_policy`` as shared, so a flavor
        that sets ``shared`` and one that omits the spec entirely are
        resize-compatible. Comparing effective policies avoids treating those two
        as different when choosing a resize target.

        Returns:
            str: ``dedicated`` if the flavor pins CPUs, otherwise ``shared``.
        """
        return "dedicated" if self.get_cpu_policy() == "dedicated" else "shared"

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return f"FlavorObject(name={self.get_name()}, id={self.get_id()}, ram={self.get_ram()}, vcpus={self.get_vcpus()}, disk={self.get_disk()}, extra_specs={self.get_extra_specs()})"
