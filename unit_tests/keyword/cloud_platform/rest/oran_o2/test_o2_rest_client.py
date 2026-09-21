"""Unit tests for the O2 REST client certificate loading and response parsing.

Verifies that initializing the O2 REST client against a directory missing a
required certificate file raises an error naming both the missing file and the
directory, and that the curl output splitter recovers the status code and body
from every shape of output curl can produce. This is lab-free: the certificate
check runs before any SSH connection is used, so a None connection is
acceptable here, and the splitter is a pure static method.
"""

import json
import os
import tempfile

import pytest

from keywords.cloud_platform.rest.oran_o2.o2_rest_client import _STATUS_MARKER, O2RestClient


def _write_empty_file(directory: str, file_name: str) -> None:
    """Create an empty file with the given name in the given directory.

    Args:
        directory (str): Directory to create the file in.
        file_name (str): Name of the file to create.
    """
    with open(os.path.join(directory, file_name), "w"):
        pass


def test_missing_client_cert_raises_naming_file_and_dir():
    """Missing client-cert.pem raises naming the file and the directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        _write_empty_file(temp_dir, O2RestClient.CLIENT_KEY_FILE)
        _write_empty_file(temp_dir, O2RestClient.CA_CERT_FILE)

        with pytest.raises(FileNotFoundError) as exc_info:
            O2RestClient(temp_dir, ssh_connection=None)

        message = str(exc_info.value)
        assert O2RestClient.CLIENT_CERT_FILE in message
        assert temp_dir in message


def test_missing_client_key_raises_naming_file_and_dir():
    """Missing client-key.pem raises naming the file and the directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        _write_empty_file(temp_dir, O2RestClient.CLIENT_CERT_FILE)
        _write_empty_file(temp_dir, O2RestClient.CA_CERT_FILE)

        with pytest.raises(FileNotFoundError) as exc_info:
            O2RestClient(temp_dir, ssh_connection=None)

        message = str(exc_info.value)
        assert O2RestClient.CLIENT_KEY_FILE in message
        assert temp_dir in message


def test_missing_ca_cert_raises_naming_file_and_dir():
    """Missing my-root-ca-cert.pem raises naming the file and the directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        _write_empty_file(temp_dir, O2RestClient.CLIENT_CERT_FILE)
        _write_empty_file(temp_dir, O2RestClient.CLIENT_KEY_FILE)

        with pytest.raises(FileNotFoundError) as exc_info:
            O2RestClient(temp_dir, ssh_connection=None)

        message = str(exc_info.value)
        assert O2RestClient.CA_CERT_FILE in message
        assert temp_dir in message


def test_split_recovers_status_and_body_from_string():
    """A string ending with the marker yields the status code and the body."""
    status_code, body = O2RestClient._split_body_and_status(f'{{"a": 1}}\n{_STATUS_MARKER}200')

    assert status_code == 200
    assert body == '{"a": 1}'


def test_split_recovers_status_and_body_from_list():
    """A list of lines as returned by the SSH layer is joined before the marker is located.

    SSHConnection.send returns stdout.readlines(), so the lines retain their
    trailing newlines even though the return type is hinted as str. This is the
    normal input shape, not an edge case.
    """
    status_code, body = O2RestClient._split_body_and_status(['{"a": 1}\n', f"{_STATUS_MARKER}404"])

    assert status_code == 404
    assert body == '{"a": 1}'


def test_split_body_from_multi_line_list_stays_valid_json():
    """A multi-line body survives the join well enough to still parse as JSON.

    Joining newline-terminated lines with a newline doubles the separators, so
    the body is not byte-identical to the response. It must still parse.
    """
    lines = ["{\n", '  "oCloudId": "abc",\n', '  "name": "x"\n', "}\n", f"{_STATUS_MARKER}200"]

    status_code, body = O2RestClient._split_body_and_status(lines)

    assert status_code == 200
    assert json.loads(body) == {"oCloudId": "abc", "name": "x"}


def test_split_without_marker_returns_zero_status_and_full_text():
    """Output with no marker yields status 0 and the whole text as the body."""
    status_code, body = O2RestClient._split_body_and_status("  curl: (60) SSL certificate problem  ")

    assert status_code == 0
    assert body == "curl: (60) SSL certificate problem"


def test_split_with_non_digit_status_returns_zero_status():
    """A non-numeric status yields 0 rather than raising."""
    status_code, body = O2RestClient._split_body_and_status(f"body\n{_STATUS_MARKER}abc")

    assert status_code == 0
    assert body == "body"


def test_split_with_empty_status_returns_zero_status():
    """A marker with nothing after it yields 0 rather than raising."""
    status_code, body = O2RestClient._split_body_and_status(f"body\n{_STATUS_MARKER}")

    assert status_code == 0
    assert body == "body"


def test_split_uses_last_marker_when_body_contains_the_marker():
    """A body containing the marker keeps the body intact and reads the real status."""
    payload = f'{{"note": "{_STATUS_MARKER}999"}}'

    status_code, body = O2RestClient._split_body_and_status(f"{payload}\n{_STATUS_MARKER}200")

    assert status_code == 200
    assert body == payload
