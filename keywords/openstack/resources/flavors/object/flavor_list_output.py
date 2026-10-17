"""Flavor list output parsing and manipulation."""

from typing import Dict, List

from framework.logging.automation_logger import get_logger

from keywords.openstack.resources.flavors.object.flavor_object import FlavorObject


class FlavorListOutput:
    """Parses and provides access to a collection of FlavorObjects."""

    def __init__(self, raw_flavors: List[Dict]) -> None:
        """Initialize FlavorListOutput from raw flavor dicts.

        Args:
            raw_flavors (List[Dict]): List of flavor dictionaries from OpenStack SDK.
        """
        self._flavors = []
        for raw in raw_flavors:
            flavor = FlavorObject()
            flavor.set_id(raw.get("id", ""))
            flavor.set_name(raw.get("name", ""))
            flavor.set_ram(raw.get("ram", 0))
            flavor.set_vcpus(raw.get("vcpus", 0))
            flavor.set_disk(raw.get("disk", 0))
            flavor.set_extra_specs(raw.get("extra_specs", {}))
            self._flavors.append(flavor)

    def get_flavors(self) -> List[FlavorObject]:
        """Get all flavor objects.

        Returns:
            List[FlavorObject]: List of flavor objects.
        """
        return self._flavors

    def get_flavor_by_name(self, name: str) -> FlavorObject:
        """Get a flavor by name.

        Args:
            name (str): Flavor name.

        Returns:
            FlavorObject: Matching flavor.

        Raises:
            ValueError: If no flavor with the given name is found.
        """
        for flavor in self._flavors:
            if flavor.get_name() == name:
                return flavor
        raise ValueError(f"Flavor '{name}' not found")

    def is_flavor_present(self, name: str) -> bool:
        """Check if a flavor with the given name exists.

        Args:
            name (str): Flavor name.

        Returns:
            bool: True if found.
        """
        for flavor in self._flavors:
            if flavor.get_name() == name:
                return True
        return False

    def discover_flavor(self) -> FlavorObject:
        """Discover a suitable boot flavor for tests, by capability not by name.

        A flavor must be huge-page backed (``hw:mem_page_size`` set) to boot on
        OVS-DPDK labs: their tenant networks use vhostuser interfaces, which
        require shared-memory guests. A flavor without it is rejected by libvirt
        with "'interface' requires shared memory" and the instance goes to ERROR.

        Selection, in order:
            1. The smallest huge-page-backed flavor (boots on DPDK and non-DPDK
               labs alike, so it is the safe default everywhere).
            2. If no flavor is huge-page backed (a non-DPDK lab where it does not
               matter), the smallest flavor overall.

        "Smallest" is ``(ram, vcpus, disk)`` with the flavor name as a final
        tiebreak, so the choice is deterministic regardless of Nova's list order.

        Returns:
            FlavorObject: Discovered boot flavor.

        Raises:
            RuntimeError: If no flavors are available.
        """
        if not self._flavors:
            raise RuntimeError("No flavors found in Nova")

        huge_page_flavors = [flavor for flavor in self._flavors if flavor.is_huge_page_backed()]
        if huge_page_flavors:
            chosen = self._smallest(huge_page_flavors)
            get_logger().log_info(f"Discovered huge-page-backed boot flavor: {chosen.get_name()} ({chosen.get_id()}), extra_specs={chosen.get_extra_specs()}")
            return chosen

        chosen = self._smallest(self._flavors)
        get_logger().log_warning(f"No huge-page-backed flavor found; using smallest flavor '{chosen.get_name()}' ({chosen.get_id()}). This will fail to schedule on an OVS-DPDK lab.")
        return chosen

    def discover_resize_flavor(self, current_flavor_name: str) -> FlavorObject:
        """Discover a resize target for the given flavor, by capability not by name.

        A resize target must be strictly larger (RAM) with a root disk at least
        as large, because Nova rejects a resize that shrinks the root disk. It
        must also match the current flavor's CPU policy: resizing a dedicated-CPU
        instance to a shared-CPU flavor (or vice versa) on a single host triggers
        a libvirt CPU unpinning error ("CPU set to unpin ... must be a subset of
        pinned CPU set"), so the policy has to be consistent across the resize.

        Selection, in order:
            1. The smallest larger flavor whose CPU policy matches the current
               flavor's.
            2. If none match the policy, the smallest larger flavor regardless of
               policy (logged, since it may fail on a single-host lab).
            3. The current flavor, if nothing larger exists.

        Args:
            current_flavor_name (str): Name of the current flavor.

        Returns:
            FlavorObject: Resize target flavor, or the current flavor if none larger exists.

        Raises:
            ValueError: If current flavor is not found.
        """
        current = self.get_flavor_by_name(current_flavor_name)
        larger = [flavor for flavor in self._flavors if flavor.get_ram() > current.get_ram() and flavor.get_disk() >= current.get_disk() and flavor.get_id() != current.get_id()]
        if not larger:
            get_logger().log_warning(f"No larger flavor found for resize of '{current_flavor_name}', using same flavor")
            return current

        policy_matched = [flavor for flavor in larger if flavor.get_effective_cpu_policy() == current.get_effective_cpu_policy()]
        if policy_matched:
            chosen = self._smallest(policy_matched)
            get_logger().log_info(f"Discovered resize flavor: {chosen.get_name()} ({chosen.get_id()}), cpu_policy='{chosen.get_effective_cpu_policy()}' matches boot flavor")
            return chosen

        chosen = self._smallest(larger)
        get_logger().log_warning(f"No larger flavor shares boot flavor's cpu_policy='{current.get_effective_cpu_policy()}'; using '{chosen.get_name()}' (cpu_policy='{chosen.get_effective_cpu_policy()}'). Same-host resize may fail.")
        return chosen

    def _smallest(self, flavors: List[FlavorObject]) -> FlavorObject:
        """Return the smallest flavor from a list, deterministically.

        Orders by ``(ram, vcpus, disk, name)`` so the result does not depend on
        Nova's listing order.

        Args:
            flavors (List[FlavorObject]): Flavors to choose from (must be non-empty).

        Returns:
            FlavorObject: The smallest flavor.
        """
        return min(flavors, key=lambda flavor: (flavor.get_ram(), flavor.get_vcpus(), flavor.get_disk(), flavor.get_name()))

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return f"FlavorListOutput(count={len(self._flavors)})"
