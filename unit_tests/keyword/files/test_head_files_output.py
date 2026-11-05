import pytest

from keywords.files.object.head_files_output import HeadFilesOutput


def test_parses_each_file_under_its_header():
    """Split head -v output into one entry per file."""
    output = HeadFilesOutput(["==> /sys/a <==\n", "1\n", "\n", "==> /sys/b <==\n", "line one\n", "line two\n"])
    assert output.get_file_contents() == {"/sys/a": "1", "/sys/b": "line one\nline two"}


def test_ignores_lines_before_the_first_header():
    """Drop output that does not belong to a file."""
    output = HeadFilesOutput("stray\n==> /sys/a <==\nvalue\n")
    assert output.get_file_contents() == {"/sys/a": "value"}


def test_empty_output_has_no_files():
    """Return nothing when no pattern matched."""
    output = HeadFilesOutput([])
    assert output.get_file_contents() == {}
    assert output.has_file("/sys/a") is False


def test_get_file_content_raises_for_missing_file():
    """Raise when asking for a file that was not read."""
    with pytest.raises(KeyError, match="/sys/missing"):
        HeadFilesOutput("==> /sys/a <==\n1\n").get_file_content("/sys/missing")


def test_missing_file_diagnostics_are_ignored():
    """Drop head diagnostics for missing files without mixing them into file content."""
    output = HeadFilesOutput("==> /sys/a <==\n1\nhead: cannot open '/sys/b*' for reading: No such file or directory\n")
    assert output.get_file_contents() == {"/sys/a": "1"}
    assert output.get_errors() == []


def test_other_diagnostics_are_reported():
    """Keep head diagnostics that are not a missing file."""
    output = HeadFilesOutput("head: cannot open '/sys/a' for reading: Permission denied\n")
    assert output.get_file_contents() == {}
    assert output.get_errors() == ["head: cannot open '/sys/a' for reading: Permission denied"]
