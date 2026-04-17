"""OpenStack flavor list data object."""


class OpenStackFlavorListObject:
    """Object to represent a single row of the 'openstack flavor list' command."""

    def __init__(self):
        """Initialize OpenStackFlavorListObject."""
        self.id = None
        self.name = None
        self.ram = None
        self.disk = None
        self.ephemeral = None
        self.vcpus = None
        self.is_public = None

    def set_id(self, id: str):
        """Set the flavor id.

        Args:
            id (str): Flavor id.
        """
        self.id = id

    def get_id(self) -> str:
        """Get the flavor id.

        Returns:
            str: Flavor id.
        """
        return self.id

    def set_name(self, name: str):
        """Set the flavor name.

        Args:
            name (str): Flavor name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get the flavor name.

        Returns:
            str: Flavor name.
        """
        return self.name

    def set_ram(self, ram: str):
        """Set the flavor RAM in MB.

        Args:
            ram (str): RAM in MB as string from CLI output.
        """
        self.ram = int(ram)

    def get_ram(self) -> int:
        """Get the flavor RAM in MB.

        Returns:
            int: RAM in MB.
        """
        return self.ram

    def set_disk(self, disk: str):
        """Set the flavor disk in GB.

        Args:
            disk (str): Disk in GB as string from CLI output.
        """
        self.disk = int(disk)

    def get_disk(self) -> int:
        """Get the flavor disk in GB.

        Returns:
            int: Disk in GB.
        """
        return self.disk

    def set_ephemeral(self, ephemeral: str):
        """Set the flavor ephemeral disk in GB.

        Args:
            ephemeral (str): Ephemeral disk in GB as string from CLI output.
        """
        self.ephemeral = int(ephemeral)

    def get_ephemeral(self) -> int:
        """Get the flavor ephemeral disk in GB.

        Returns:
            int: Ephemeral disk in GB.
        """
        return self.ephemeral

    def get_total_disk(self) -> int:
        """Get the total disk requirement (disk + ephemeral) in GB.

        Returns:
            int: Total disk in GB.
        """
        return self.disk + self.ephemeral

    def set_vcpus(self, vcpus: str):
        """Set the flavor vCPU count.

        Args:
            vcpus (str): vCPU count as string from CLI output.
        """
        self.vcpus = int(vcpus)

    def get_vcpus(self) -> int:
        """Get the flavor vCPU count.

        Returns:
            int: vCPU count.
        """
        return self.vcpus

    def set_is_public(self, is_public: str):
        """Set whether the flavor is public.

        Args:
            is_public (str): 'True' or 'False' string from CLI output.
        """
        self.is_public = is_public

    def get_is_public(self) -> str:
        """Get whether the flavor is public.

        Returns:
            str: 'True' or 'False' string.
        """
        return self.is_public

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Human-readable flavor summary.
        """
        return f"Flavor(id={self.id}, name={self.name}, " f"vcpus={self.vcpus}, ram={self.ram}MB, " f"disk={self.disk}GB, ephemeral={self.ephemeral}GB)"
