"""Df command output collection."""

from typing import List

from keywords.linux.df.df_object import DfObject


class DfOutput:
    """Collection of df command results."""

    def __init__(self, raw_output: List[str]):
        """Initialize df output collection.

        Args:
            raw_output (List[str]): Raw output lines from df command.
        """
        # Initialize empty collection to store parsed df entries
        self.df_entries: List[DfObject] = []
        self._parse_df_output(raw_output)

    def _parse_df_output(self, raw_output: List[str]) -> None:
        """Parse df command output into DfObject instances.

        Args:
            raw_output (List[str]): Raw output lines from df command.
        """
        # Skip header line (first line contains column names)
        for line in raw_output[1:]:
            if line.strip():
                parts = line.strip().split()
                # Ensure we have all required fields (filesystem, size, used, avail, use%, mounted)
                if len(parts) >= 6:
                    filesystem = parts[0]  # Device/filesystem name
                    total_kb = int(parts[1])  # Total space in KB
                    used_kb = int(parts[2])  # Used space in KB
                    available_kb = int(parts[3])  # Available space in KB
                    usage_percent = int(parts[4].rstrip("%"))  # Usage percentage (remove % symbol)
                    mount_point = parts[5]  # Mount point path

                    # Create df object and add to collection
                    df_obj = DfObject(filesystem, total_kb, used_kb, available_kb, usage_percent, mount_point)
                    self.df_entries.append(df_obj)

    def get_df_entries(self) -> List[DfObject]:
        """Get all df entries.

        Returns:
            List[DfObject]: List of all df entries.
        """
        return self.df_entries

    def get_df_by_mount_point(self, mount_point: str) -> DfObject:
        """Get df entry by mount point.

        Args:
            mount_point (str): Mount point path.

        Returns:
            DfObject: Df entry for the specified mount point.

        Raises:
            ValueError: If mount point not found.
        """
        # Search through all entries for matching mount point
        for entry in self.df_entries:
            if entry.get_mount_point() == mount_point:
                return entry
        raise ValueError(f"Mount point '{mount_point}' not found")

    def get_first_entry(self) -> DfObject:
        """Get first df entry.

        Returns:
            DfObject: First df entry.

        Raises:
            ValueError: If no entries available.
        """
        # Return first entry (useful for single filesystem queries)
        if not self.df_entries:
            raise ValueError("No df entries available")
        return self.df_entries[0]
