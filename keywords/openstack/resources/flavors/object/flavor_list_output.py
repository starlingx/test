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
        """Discover a suitable flavor for tests.

        Prefers m1.tiny, then m1.small, then the smallest available.

        Returns:
            FlavorObject: Discovered flavor.

        Raises:
            RuntimeError: If no flavors are available.
        """
        if not self._flavors:
            raise RuntimeError("No flavors found in Nova")

        for preferred in ["m1.tiny", "m1.small"]:
            if self.is_flavor_present(preferred):
                flavor = self.get_flavor_by_name(preferred)
                get_logger().log_info(f"Discovered flavor: {flavor.get_name()} ({flavor.get_id()})")
                return flavor

        smallest = min(self._flavors, key=lambda f: (f.get_ram(), f.get_vcpus(), f.get_disk()))
        get_logger().log_info(f"No m1.tiny/m1.small found, using smallest: {smallest.get_name()} ({smallest.get_id()})")
        return smallest

    def discover_resize_flavor(self, current_flavor_name: str) -> FlavorObject:
        """Discover a flavor larger than the given one for resize tests.

        Args:
            current_flavor_name (str): Name of the current flavor.

        Returns:
            FlavorObject: Larger flavor, or current flavor if none larger exists.

        Raises:
            ValueError: If current flavor is not found.
        """
        current = self.get_flavor_by_name(current_flavor_name)
        larger = [f for f in self._flavors if f.get_ram() > current.get_ram() and f.get_id() != current.get_id()]
        if larger:
            resize = min(larger, key=lambda f: f.get_ram())
            get_logger().log_info(f"Discovered resize flavor: {resize.get_name()} ({resize.get_id()})")
            return resize

        get_logger().log_warning("No larger flavor found for resize tests, using same flavor")
        return current

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return f"FlavorListOutput(count={len(self._flavors)})"
