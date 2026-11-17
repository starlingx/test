"""Unit tests for LogGrepKeywords.count_pattern_occurrences.

The keyword counts matching lines in a root-owned log so a caller can compare two counts taken
some time apart. These tests cover the count parsing, the failure on a missing file (which must
not be reported as a count of 0) and the quoting of the command sent over SSH.
"""

import shlex
import unittest
from typing import Union
from unittest.mock import NonCallableMagicMock, patch

from framework.exceptions.keyword_exception import KeywordException
from keywords.linux.log.log_grep_keywords import LogGrepKeywords

LOG_PATH = "/var/log/dcorch/dcorch-engine.log"


class TestCountPatternOccurrences(unittest.TestCase):
    """Test suite for LogGrepKeywords.count_pattern_occurrences."""

    def setUp(self):
        """Silence the BaseKeyword logger and build the keyword with a mocked SSH connection."""
        self.logger_patcher = patch("keywords.base_keyword.get_logger")
        self.logger_patcher.start()
        self.ssh_connection = NonCallableMagicMock()
        self.keywords = LogGrepKeywords(self.ssh_connection)

    def tearDown(self):
        """Stop the logger patcher."""
        self.logger_patcher.stop()

    def _set_output(self, output: Union[list, str]) -> None:
        """Set what the mocked sudo call returns.

        Args:
            output (Union[list, str]): the value returned by send_as_sudo_non_interactive.
        """
        self.ssh_connection.send_as_sudo_non_interactive.return_value = output

    def _sent_command(self) -> str:
        """Return the single command passed to send_as_sudo_non_interactive.

        Returns:
            str: the command string.
        """
        self.ssh_connection.send_as_sudo_non_interactive.assert_called_once()
        return self.ssh_connection.send_as_sudo_non_interactive.call_args.args[0]

    def test_returns_count_from_list_output(self):
        """The count is read from the list of lines the SSH layer returns."""
        self._set_output(["7\n"])
        self.assertEqual(self.keywords.count_pattern_occurrences(LOG_PATH, "put_users"), 7)

    def test_returns_count_from_string_output(self):
        """The count is read when the output is a plain string."""
        self._set_output("12\n")
        self.assertEqual(self.keywords.count_pattern_occurrences(LOG_PATH, "put_users"), 12)

    def test_zero_matches_returns_zero(self):
        """A readable file with no matching line gives 0."""
        self._set_output(["0\n"])
        self.assertEqual(self.keywords.count_pattern_occurrences(LOG_PATH, "put_users"), 0)

    def test_count_is_taken_from_last_numeric_line(self):
        """Stray non-numeric output before the count is ignored."""
        self._set_output(["some warning\n", "3\n"])
        self.assertEqual(self.keywords.count_pattern_occurrences(LOG_PATH, "put_users"), 3)

    def test_missing_file_raises_instead_of_returning_zero(self):
        """No output means the file could not be read, which must not look like a count of 0."""
        self._set_output([])
        with self.assertRaises(KeywordException):
            self.keywords.count_pattern_occurrences(LOG_PATH, "put_users")

    def test_empty_string_output_raises(self):
        """An empty string is treated the same as no output."""
        self._set_output("")
        with self.assertRaises(KeywordException):
            self.keywords.count_pattern_occurrences(LOG_PATH, "put_users")

    def test_non_numeric_output_raises(self):
        """Output that holds no count raises."""
        self._set_output(["grep: /var/log/x: Permission denied\n"])
        with self.assertRaises(KeywordException):
            self.keywords.count_pattern_occurrences(LOG_PATH, "put_users")

    def test_single_pattern_command(self):
        """One pattern builds a fixed-string grep guarded by 'test -f' and counted with wc -l."""
        self._set_output(["1\n"])
        self.keywords.count_pattern_occurrences(LOG_PATH, "put_users")

        outer = shlex.split(self._sent_command())
        self.assertEqual(outer[:2], ["sh", "-c"])
        self.assertEqual(outer[2], f"test -f {LOG_PATH} && grep -F -e put_users {LOG_PATH} | wc -l")

    def test_secondary_pattern_and_ignore_case_command(self):
        """A secondary pattern adds a second grep, and ignore_case adds -i to both."""
        self._set_output(["1\n"])
        self.keywords.count_pattern_occurrences(LOG_PATH, "put_users", secondary_pattern="admin", ignore_case=True)

        inner = shlex.split(self._sent_command())[2]
        self.assertEqual(inner, f"test -f {LOG_PATH} && grep -F -i -e put_users {LOG_PATH} | grep -F -i -e admin | wc -l")

    def test_pattern_with_shell_metacharacters_is_quoted(self):
        """A pattern holding quotes, spaces and shell operators reaches grep as one literal argument."""
        pattern = 'it\'s a "test"; rm -rf / $(id)'
        self._set_output(["0\n"])
        self.keywords.count_pattern_occurrences(LOG_PATH, pattern)

        inner = shlex.split(self._sent_command())[2]
        grep_part = inner.split(" && ", 1)[1].split(" | wc -l")[0]
        self.assertEqual(shlex.split(grep_part), ["grep", "-F", "-e", pattern, LOG_PATH])

    def test_log_path_with_space_is_quoted(self):
        """A log path with a space stays one argument."""
        path = "/var/log/my logs/dcorch.log"
        self._set_output(["0\n"])
        self.keywords.count_pattern_occurrences(path, "put_users")

        inner = shlex.split(self._sent_command())[2]
        grep_part = inner.split(" && ", 1)[1].split(" | wc -l")[0]
        self.assertEqual(shlex.split(grep_part)[-1], path)


if __name__ == "__main__":
    unittest.main()
