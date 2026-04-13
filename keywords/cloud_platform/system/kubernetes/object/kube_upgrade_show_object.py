from typing import Optional


class KubeUpgradeShowObject:
    """Represents the output of a 'system kube-upgrade-show' vertical table row.

    Typical output:
    +------------------+--------------------------------------+
    | Property         | Value                                |
    +------------------+--------------------------------------+
    | uuid             | 12345678-abcd-...                    |
    | from_version     | v1.31.5                              |
    | to_version       | v1.32.2                              |
    | state            | upgrade-started                      |
    | created_at       | 2025-01-01T00:00:00.000000+00:00     |
    | updated_at       | 2025-01-01T00:01:00.000000+00:00     |
    +------------------+--------------------------------------+
    """

    def __init__(self) -> None:
        """Initializes a KubeUpgradeShowObject with default values."""
        self.uuid: Optional[str] = None
        self.from_version: Optional[str] = None
        self.to_version: Optional[str] = None
        self.state: Optional[str] = None
        self.created_at: Optional[str] = None
        self.updated_at: Optional[str] = None

    def get_uuid(self) -> Optional[str]:
        """Getter for uuid.

        Returns:
            Optional[str]: The uuid value.
        """
        return self.uuid

    def set_uuid(self, uuid: str) -> None:
        """Setter for uuid.

        Args:
            uuid (str): The uuid value.
        """
        self.uuid = uuid

    def get_from_version(self) -> Optional[str]:
        """Getter for from_version.

        Returns:
            Optional[str]: The source kubernetes version.
        """
        return self.from_version

    def set_from_version(self, from_version: str) -> None:
        """Setter for from_version.

        Args:
            from_version (str): The source kubernetes version.
        """
        self.from_version = from_version

    def get_to_version(self) -> Optional[str]:
        """Getter for to_version.

        Returns:
            Optional[str]: The target kubernetes version.
        """
        return self.to_version

    def set_to_version(self, to_version: str) -> None:
        """Setter for to_version.

        Args:
            to_version (str): The target kubernetes version.
        """
        self.to_version = to_version

    def get_state(self) -> Optional[str]:
        """Getter for state.

        Returns:
            Optional[str]: The upgrade state.
        """
        return self.state

    def set_state(self, state: str) -> None:
        """Setter for state.

        Args:
            state (str): The upgrade state.
        """
        self.state = state

    def get_created_at(self) -> Optional[str]:
        """Getter for created_at.

        Returns:
            Optional[str]: The creation timestamp.
        """
        return self.created_at

    def set_created_at(self, created_at: str) -> None:
        """Setter for created_at.

        Args:
            created_at (str): The creation timestamp.
        """
        self.created_at = created_at

    def get_updated_at(self) -> Optional[str]:
        """Getter for updated_at.

        Returns:
            Optional[str]: The last update timestamp.
        """
        return self.updated_at

    def set_updated_at(self, updated_at: str) -> None:
        """Setter for updated_at.

        Args:
            updated_at (str): The last update timestamp.
        """
        self.updated_at = updated_at

    def __str__(self) -> str:
        """Returns a human-readable string representation.

        Returns:
            str: String representation of the kubernetes upgrade object.
        """
        return f"KubeUpgradeShowObject(" f"uuid={self.uuid}, " f"from_version={self.from_version}, " f"to_version={self.to_version}, " f"state={self.state}, " f"created_at={self.created_at}, " f"updated_at={self.updated_at})"
