import shlex
from typing import Optional

from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class LogGrepKeywords(BaseKeyword):
    """Keywords for searching log files that require sudo access."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initialize LogGrepKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        super().__init__()
        self.ssh_connection = ssh_connection

    def grep_log_for_errors(self, log_path: str, pattern: str, secondary_pattern: Optional[str] = None, tail: int = 5) -> str:
        """Grep a log file for error patterns using sudo, returning matching lines.

        Uses ``SSHConnection.send_as_sudo_non_interactive()`` to access log files
        not readable by sysadmin. Returns an empty string if no matches are found
        (uses '|| true' to avoid non-zero exit codes).

        Args:
            log_path (str): Absolute path to the log file to search.
            pattern (str): Primary grep pattern (case-insensitive).
            secondary_pattern (Optional[str]): Optional secondary grep pattern to
                further filter results (case-insensitive). Defaults to None.
            tail (int): Number of trailing lines to return. Defaults to 5.

        Returns:
            str: Matching log lines, or empty string if no matches found.
        """
        if secondary_pattern:
            grep_pipeline = f'grep -i "{pattern}" {log_path} 2>/dev/null ' f'| grep -i "{secondary_pattern}" ' f"| tail -{tail} || true"
        else:
            grep_pipeline = f'grep -i "{pattern}" {log_path} 2>/dev/null ' f"| tail -{tail} || true"

        output = self.ssh_connection.send_as_sudo_non_interactive(f"sh -c '{grep_pipeline}'")
        if isinstance(output, list):
            return "\n".join(output).strip()
        return output.strip()

    def count_pattern_occurrences(self, log_path: str, pattern: str, secondary_pattern: Optional[str] = None, ignore_case: bool = False) -> int:
        """Count the lines of a log file that match a pattern, using sudo.

        Unlike ``grep_log_for_errors()``, which returns the last few matching lines,
        this returns how many lines match, so a caller can take a count at two points
        in time and tell whether an event is repeating. Patterns are matched as fixed
        strings (not regular expressions) and are shell-quoted, so they may contain
        any character.

        A missing or unreadable log file raises instead of returning 0. A count of 0
        from a file that does not exist would look the same as "the event did not
        happen" and let a repetition check pass without ever reading the log.

        The count covers the whole file. If the log is rotated between two calls the
        second count can be lower than the first, so callers comparing counts should
        treat a decrease as a rotation, not as fewer events.

        Args:
            log_path (str): Absolute path to the log file to search.
            pattern (str): Primary fixed-string pattern. A line must contain it to count.
            secondary_pattern (Optional[str]): Optional fixed-string pattern that a line
                must also contain to count. Defaults to None.
            ignore_case (bool): Whether matching ignores case. Defaults to False.

        Returns:
            int: Number of lines matching every supplied pattern. 0 if the file exists
                and nothing matches.

        Raises:
            KeywordException: If the log file does not exist or is not readable, or if
                the command output does not contain a count.
        """
        grep_options = "-F -i" if ignore_case else "-F"
        quoted_path = shlex.quote(log_path)

        pipeline = f"grep {grep_options} -e {shlex.quote(pattern)} {quoted_path}"
        if secondary_pattern:
            pipeline += f" | grep {grep_options} -e {shlex.quote(secondary_pattern)}"
        # The leading 'test -f' makes a missing file produce no output at all. 'wc -l' always
        # prints a number, so an empty output can only mean the file could not be read.
        count_command = f"test -f {quoted_path} && {pipeline} | wc -l"

        output = self.ssh_connection.send_as_sudo_non_interactive(f"sh -c {shlex.quote(count_command)}")
        lines = output if isinstance(output, list) else str(output).splitlines()
        for line in reversed(lines):
            stripped_line = line.strip()
            if stripped_line.isdigit():
                return int(stripped_line)

        raise KeywordException(f"Could not count occurrences of '{pattern}' in '{log_path}': the file is missing, unreadable, or the command returned no count. Output: {output!r}")
