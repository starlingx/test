"""Keyring file info object for LUKS keyring validation."""


class KeyringFileInfo:
    """Represents file metadata for a keyring file."""

    def __init__(self, owner: str, group: str, permissions: str, path: str):
        """Initialize keyring file info.

        Args:
            owner (str): File owner.
            group (str): File group.
            permissions (str): Octal permissions string.
            path (str): File path.
        """
        self._owner = owner
        self._group = group
        self._permissions = permissions
        self._path = path

    def get_owner(self) -> str:
        """Get file owner.

        Returns:
            str: File owner.
        """
        return self._owner

    def get_group(self) -> str:
        """Get file group.

        Returns:
            str: File group.
        """
        return self._group

    def get_permissions(self) -> str:
        """Get file permissions.

        Returns:
            str: Octal permissions string.
        """
        return self._permissions

    def get_path(self) -> str:
        """Get file path.

        Returns:
            str: File path.
        """
        return self._path

    def has_world_access(self) -> bool:
        """Check if file has world-readable/writable access.

        Returns:
            bool: True if world bits are non-zero.
        """
        return self._permissions[-1] != "0"
