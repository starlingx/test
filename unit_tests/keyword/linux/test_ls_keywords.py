from collections.abc import Iterator
from unittest.mock import NonCallableMagicMock, patch

import pytest

from keywords.linux.ls.ls_keywords import LsKeywords

PATTERN = "/usr/local/share/applications/helm/*reloader*"


@pytest.fixture(autouse=True)
def _silence_keyword_logger() -> Iterator[None]:
    """Silence the logger BaseKeyword wraps every call with, which needs configuration to exist.

    Yields:
        None: for the duration of each test.
    """
    with patch("keywords.base_keyword.get_logger"):
        yield


def _keywords(output: object, return_code: object) -> LsKeywords:
    """Build an LsKeywords wired to a stand-in SSH connection.

    Args:
        output (object): what send() returns.
        return_code (object): what get_return_code() returns afterwards.

    Returns:
        LsKeywords: an instance whose SSH connection answers with the given pair.
    """
    ssh_connection = NonCallableMagicMock()
    ssh_connection.send = lambda *args, **kwargs: output
    ssh_connection.get_return_code = lambda: return_code
    return LsKeywords(ssh_connection)


def test_matches_are_returned_stripped():
    """A successful listing returns one entry per line, with the whitespace removed."""
    keywords = _keywords(["/path/reloader-26.10-4.tgz\n"], 0)
    assert keywords.get_matching_files(PATTERN) == ["/path/reloader-26.10-4.tgz"]


def test_several_matches_are_all_returned():
    """Every match is returned, so a caller can tell one match from many."""
    keywords = _keywords(["/path/a.tgz\n", "/path/b.tgz\n"], 0)
    assert keywords.get_matching_files(PATTERN) == ["/path/a.tgz", "/path/b.tgz"]


def test_a_string_output_is_accepted():
    """send() returns a string on some paths rather than a list of lines."""
    keywords = _keywords("/path/reloader-26.10-4.tgz\n", 0)
    assert keywords.get_matching_files(PATTERN) == ["/path/reloader-26.10-4.tgz"]


def test_blank_lines_are_discarded():
    """A trailing newline must not become an empty match that reads as a hit."""
    keywords = _keywords(["/path/a.tgz\n", "\n", "   \n"], 0)
    assert keywords.get_matching_files(PATTERN) == ["/path/a.tgz"]


def test_no_match_returns_an_empty_list_rather_than_raising():
    """ls exits non-zero when a pattern matches nothing, which is an answer, not a failure.

    This is the distinction the method exists to draw. A caller asserting a precondition needs to
    tell "the file is not there" from "I could not ask", and an exception for the first case forces
    it to catch broadly and lose the second.
    """
    keywords = _keywords(["ls: cannot access '...': No such file or directory"], 2)
    assert keywords.get_matching_files(PATTERN) == []


def test_an_unreadable_return_code_raises():
    """A return code that could not be read back means the command's fate is unknown.

    get_return_code returns None when the value could not be read, which happens when the probe
    times out. Treating that as "no match" would report a missing file on a system that never
    answered.
    """
    keywords = _keywords(None, None)
    with pytest.raises(Exception):
        keywords.get_matching_files(PATTERN)


def test_a_negative_return_code_raises():
    """-1 is reported when the prompt read itself failed, on a timeout or a closed channel."""
    keywords = _keywords(None, -1)
    with pytest.raises(Exception):
        keywords.get_matching_files(PATTERN)
