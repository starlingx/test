"""Df command output object."""


class DfObject:
    """Container for df command output data."""

    def __init__(self, filesystem: str, total_kb: int, used_kb: int, available_kb: int, usage_percent: int, mount_point: str):
        """Initialize df object with parsed data.

        Args:
            filesystem (str): Filesystem name/device.
            total_kb (int): Total space in kilobytes.
            used_kb (int): Used space in kilobytes.
            available_kb (int): Available space in kilobytes.
            usage_percent (int): Usage percentage (0-100).
            mount_point (str): Mount point path.
        """
        self.filesystem = filesystem
        self.total_kb = total_kb
        self.used_kb = used_kb
        self.available_kb = available_kb
        self.usage_percent = usage_percent
        self.mount_point = mount_point

    def get_usage_percentage(self) -> int:
        """Get usage percentage as integer.

        Returns:
            int: Usage percentage (0-100).
        """
        return self.usage_percent

    def get_total_kb(self) -> int:
        """Get total space in kilobytes.

        Returns:
            int: Total space in KB.
        """
        return self.total_kb

    def get_used_kb(self) -> int:
        """Get used space in kilobytes.

        Returns:
            int: Used space in KB.
        """
        return self.used_kb

    def get_filesystem(self) -> str:
        """Get filesystem name.

        Returns:
            str: Filesystem name/device.
        """
        return self.filesystem

    def get_mount_point(self) -> str:
        """Get mount point path.

        Returns:
            str: Mount point path.
        """
        return self.mount_point
