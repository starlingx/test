"""Unit tests for CurlKeywords.find_file_in_directory_listing()."""

from unittest.mock import NonCallableMock, patch

import pytest

from keywords.files.curl_keywords import CurlKeywords


def find_file(output: object, exclude_pattern: str = None) -> tuple:
    """Run find_file_in_directory_listing() against a mocked SSH connection.

    Args:
        output (object): What the SSH connection returns for the command.
        exclude_pattern (str): Exclude pattern to pass. Defaults to None.

    Returns:
        tuple: The returned file name and the command sent.
    """
    ssh_connection = NonCallableMock()
    ssh_connection.send.return_value = output
    with patch("keywords.base_keyword.get_logger"), patch("keywords.files.curl_keywords.get_logger"):
        file_name = CurlKeywords(ssh_connection).find_file_in_directory_listing("http://server/dir/", "my-app-[0-9]", ".tgz", exclude_pattern)
    return file_name, ssh_connection.send.call_args.args[0]


def test_returns_the_matching_file_name():
    """The file name the command finds is returned without surrounding whitespace."""
    file_name, cmd = find_file(["my-app-1.0-0.tgz\n"])
    assert file_name == "my-app-1.0-0.tgz"
    assert cmd == "curl -s http://server/dir/ | grep -o 'my-app-[0-9][^\"<]*\\.tgz' | head -1"


def test_skips_names_matching_the_exclude_pattern():
    """The exclude pattern is applied before the first name is taken."""
    _, cmd = find_file("my-app-1.0-0.tgz", exclude_pattern="debug")
    assert cmd == "curl -s http://server/dir/ | grep -o 'my-app-[0-9][^\"<]*\\.tgz' | grep -v debug | head -1"


def test_raises_when_nothing_matches():
    """An empty result raises instead of returning an empty name."""
    with pytest.raises(RuntimeError, match="No file matching 'my-app-\\[0-9\\]...\\.tgz' found"):
        find_file([])
