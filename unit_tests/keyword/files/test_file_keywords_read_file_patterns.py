from unittest.mock import MagicMock, patch

import pytest

from framework.exceptions.keyword_exception import KeywordException
from keywords.files.file_keywords import FileKeywords


class FakeSshConnection:
    """SSH double; a plain class because BaseKeyword wraps callable attributes such as MagicMock."""

    def __init__(self, output: list[str], return_code: int):
        """Constructor.

        Args:
            output (list[str]): Lines returned by the SSH command.
            return_code (int): Return code of the SSH command.
        """
        self.output = output
        self.return_code = return_code
        self.commands = []
        self.sudo_commands = []

    def send(self, command: str) -> list[str]:
        """Record the command and return the canned output.

        Args:
            command (str): Command sent.

        Returns:
            list[str]: Canned output lines.
        """
        self.commands.append(command)
        return self.output

    def send_as_sudo_non_interactive(self, command: str) -> list[str]:
        """Record the sudo command and return the canned output.

        Args:
            command (str): Command sent.

        Returns:
            list[str]: Canned output lines.
        """
        self.sudo_commands.append(command)
        return self.output

    def get_return_code(self) -> int:
        """Get the canned return code.

        Returns:
            int: Return code.
        """
        return self.return_code


@patch("keywords.base_keyword.get_logger", MagicMock())
def test_read_file_patterns_returns_existing_files():
    """Return the files that exist when head exits 0."""
    ssh_connection = FakeSshConnection(["==> /sys/a <==\n", "1\n"], 0)
    output = FileKeywords(ssh_connection).read_file_patterns(["/sys/a"])
    assert output.get_file_contents() == {"/sys/a": "1"}
    assert "2>&1" in ssh_connection.commands[0]


@patch("keywords.base_keyword.get_logger", MagicMock())
def test_read_file_patterns_ignores_missing_files():
    """Accept head exit status 1 when the only diagnostics are missing files."""
    ssh_connection = FakeSshConnection(["==> /sys/a <==\n", "1\n", "head: cannot open '/sys/b' for reading: No such file or directory\n"], 1)
    output = FileKeywords(ssh_connection).read_file_patterns(["/sys/a", "/sys/b"])
    assert output.get_file_contents() == {"/sys/a": "1"}


@patch("keywords.base_keyword.get_logger", MagicMock())
def test_read_file_patterns_raises_on_permission_error():
    """Raise instead of returning partial data when a file cannot be read."""
    ssh_connection = FakeSshConnection(["head: cannot open '/sys/a' for reading: Permission denied\n"], 1)
    with pytest.raises(KeywordException, match="Permission denied"):
        FileKeywords(ssh_connection).read_file_patterns(["/sys/a"])


@patch("keywords.base_keyword.get_logger", MagicMock())
def test_read_file_patterns_raises_on_ssh_failure():
    """Raise when the command itself fails, such as a lost connection."""
    ssh_connection = FakeSshConnection([], 255)
    with pytest.raises(KeywordException, match="return code 255"):
        FileKeywords(ssh_connection).read_file_patterns(["/sys/a"])


@patch("keywords.base_keyword.get_logger", MagicMock())
def test_read_file_patterns_with_sudo_keeps_head_diagnostics_in_output():
    """Run the whole head command in a root shell so its diagnostics are still captured."""
    ssh_connection = FakeSshConnection(["==> /sys/a <==\n", "1\n"], 0)
    FileKeywords(ssh_connection).read_file_patterns(["/sys/a"], use_sudo=True)
    assert ssh_connection.commands == []
    assert ssh_connection.sudo_commands == ["sh -c 'head -v -c 4096 -- /sys/a 2>&1'"]
