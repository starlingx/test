"""Linux find command keywords."""

import shlex
from typing import Optional

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_is_digit, validate_not_none
from keywords.base_keyword import BaseKeyword


class FindKeywords(BaseKeyword):
    """Generic find command operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize find keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection for file operations.
        """
        super().__init__()
        self.ssh_connection = ssh_connection

    def count_files_in_directory(self, directory_path: str, file_pattern: str = "*", max_depth: int = 1, min_depth: int = 0, file_type: str = "f", exclude_pattern: Optional[str] = None) -> int:
        """Count files/directories matching pattern in directory.

        Args:
            directory_path (str): Directory path to search.
            file_pattern (str): File pattern to match. Defaults to '*'.
            max_depth (int): Maximum search depth. Defaults to 1.
            min_depth (int): Minimum search depth. Defaults to 0.
            file_type (str): Type filter ('f' for files, 'd' for directories). Defaults to 'f'.
            exclude_pattern (Optional[str]): Pattern to exclude from results. Defaults to None.

        Returns:
            int: Number of matching files/directories.
        """
        safe_directory_path = shlex.quote(directory_path)
        safe_file_pattern = shlex.quote(file_pattern)
        find_cmd = f"find {safe_directory_path}"

        if min_depth > 0:
            find_cmd += f" -mindepth {min_depth}"
        find_cmd += f" -maxdepth {max_depth} -type {file_type} -name {safe_file_pattern}"

        if exclude_pattern:
            safe_exclude_pattern = shlex.quote(exclude_pattern)
            find_cmd += f" | grep -v {safe_exclude_pattern}"
        find_cmd += " | wc -l"

        get_logger().log_info(f"DEBUG: Executing find command: {find_cmd}")

        result = self.ssh_connection.send(find_cmd)
        self.validate_success_return_code(self.ssh_connection)

        validate_not_none(result, f"file count command response for pattern {file_pattern}")
        count_str = result[0].strip()
        validate_is_digit(count_str, f"file count string for pattern {file_pattern}")
        return int(count_str)

    def find_most_recent_file(self, directory_path: str, file_pattern: str = "*", max_depth: int = 1, min_depth: int = 0) -> Optional[str]:
        """Find most recent file matching pattern in directory.

        Args:
            directory_path (str): Directory path to search.
            file_pattern (str): File pattern to match. Defaults to '*'.
            max_depth (int): Maximum search depth. Defaults to 1.
            min_depth (int): Minimum search depth. Defaults to 0.

        Returns:
            Optional[str]: Path to most recent file, or None if no files found.
        """
        safe_directory_path = shlex.quote(directory_path)
        find_cmd = f"find {safe_directory_path}"

        if min_depth > 0:
            find_cmd += f" -mindepth {min_depth}"
        safe_file_pattern = shlex.quote(file_pattern)
        find_cmd += f" -maxdepth {max_depth} -type f -name {safe_file_pattern} -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-"

        result = self.ssh_connection.send(find_cmd)
        self.validate_success_return_code(self.ssh_connection)

        if result and result[0].strip():
            return result[0].strip()
        return None
