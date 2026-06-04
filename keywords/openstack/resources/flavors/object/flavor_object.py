"""Flavor object representation."""


class FlavorObject:
    """Represents a single OpenStack flavor."""

    def __init__(self) -> None:
        """Initialize an empty FlavorObject."""
        self._properties = {}

    def set_property(self, key: str, value: object) -> None:
        """Set a property value.

        Args:
            key (str): Property name.
            value (object): Property value.
        """
        self._properties[key] = value

    def get_property(self, key: str) -> object:
        """Get a property value.

        Args:
            key (str): Property name.

        Returns:
            object: Property value.
        """
        return self._properties.get(key)

    def get_id(self) -> str:
        """Get the flavor ID.

        Returns:
            str: Flavor ID.
        """
        return self._properties.get("id", "")

    def set_id(self, flavor_id: str) -> None:
        """Set the flavor ID.

        Args:
            flavor_id (str): Flavor ID.
        """
        self._properties["id"] = flavor_id

    def get_name(self) -> str:
        """Get the flavor name.

        Returns:
            str: Flavor name.
        """
        return self._properties.get("name", "")

    def set_name(self, name: str) -> None:
        """Set the flavor name.

        Args:
            name (str): Flavor name.
        """
        self._properties["name"] = name

    def get_ram(self) -> int:
        """Get the RAM in MB.

        Returns:
            int: RAM in MB.
        """
        return self._properties.get("ram", 0)

    def set_ram(self, ram: int) -> None:
        """Set the RAM in MB.

        Args:
            ram (int): RAM in MB.
        """
        self._properties["ram"] = ram

    def get_vcpus(self) -> int:
        """Get the number of vCPUs.

        Returns:
            int: Number of vCPUs.
        """
        return self._properties.get("vcpus", 0)

    def set_vcpus(self, vcpus: int) -> None:
        """Set the number of vCPUs.

        Args:
            vcpus (int): Number of vCPUs.
        """
        self._properties["vcpus"] = vcpus

    def get_disk(self) -> int:
        """Get the disk size in GB.

        Returns:
            int: Disk size in GB.
        """
        return self._properties.get("disk", 0)

    def set_disk(self, disk: int) -> None:
        """Set the disk size in GB.

        Args:
            disk (int): Disk size in GB.
        """
        self._properties["disk"] = disk

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return f"FlavorObject(name={self.get_name()}, id={self.get_id()}, ram={self.get_ram()}, vcpus={self.get_vcpus()}, disk={self.get_disk()})"
