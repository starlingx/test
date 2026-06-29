"""Output parser for keyring file listing."""

from typing import Union

from keywords.cloud_platform.security.luks_keyring.objects.keyring_file_info import KeyringFileInfo


class KeyringFileInfoOutput:
    """Parser for stat command output into KeyringFileInfo objects.

    Parses output from: stat -c '%a %U %G %n' <file>
    Example line: 640 root sys_protected /var/luks/stx/luks_fs/controller/.keyring/26.10/python_keyring/.keyring_secret
    """

    def __init__(self, command_output: Union[str, list[str]]):
        """Initialize output parser.

        Args:
            command_output (Union[str, list[str]]): Raw stat command output.
        """
        if isinstance(command_output, str):
            command_output = command_output.strip().splitlines()
        self._files = self._parse(command_output)

    def _parse(self, lines: list[str]) -> list[KeyringFileInfo]:
        """Parse stat output lines into KeyringFileInfo objects.

        Args:
            lines (list[str]): Output lines from stat command.

        Returns:
            list[KeyringFileInfo]: Parsed file info objects.
        """
        results = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 3)
            if len(parts) >= 4:
                results.append(KeyringFileInfo(
                    permissions=parts[0],
                    owner=parts[1],
                    group=parts[2],
                    path=parts[3],
                ))
        return results

    def get_files(self) -> list[KeyringFileInfo]:
        """Get all parsed file info objects.

        Returns:
            list[KeyringFileInfo]: List of file info objects.
        """
        return self._files

    def get_file(self, path: str) -> KeyringFileInfo:
        """Get file info by path.

        Args:
            path (str): File path to find.

        Returns:
            KeyringFileInfo: Matching file info, or None if not found.
        """
        for f in self._files:
            if f.get_path() == path:
                return f
        return None
