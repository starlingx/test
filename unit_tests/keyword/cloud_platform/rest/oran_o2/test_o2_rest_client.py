"""Unit tests for the O2 REST client certificate loading and response parsing.

Verifies that initializing the O2 REST client against a directory missing a
required certificate file raises an error naming both the missing file and the
directory, and that the curl output splitter recovers the status code and body
from every shape of output curl can produce. This is lab-free: the certificate
check runs before any SSH connection is used, so a None connection is
acceptable here, and the splitter is a pure static method.

Also verifies how a PATCH request is constructed, driven through the client's real
send path with a mocked connection rather than through an extracted command builder,
so the assertions cannot pass while the production path stops using them. The
credential assertions are the point of that: the token is supplied to the
constructor and proven absent from the command handed to the SSH layer, which logs
every command verbatim.
"""

import json
import os
import tempfile
from unittest.mock import NonCallableMagicMock, patch

import pytest

from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManager
from framework.ssh.ssh_connection import SSHConnection
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


# Supplied to the client so the tests can prove it never reaches the command string.
# Not a real credential.
_TEST_TOKEN = "a-token-value"

# A controller-local URL, so no lab address appears in this file.
_ALARM_URL = "https://localhost:30205/o2ims-infrastructureMonitoring/v1/alarms/abc"

# A body shaped like the one the alarm clear path sends.
_ALARM_BODY = '{"perceivedSeverity": "5"}'


def _build_client_with_mock_connection(cert_dir: str, send_output: str) -> O2RestClient:
    """Build a client whose connection is mocked, so requests are observable.

    Three things have to be arranged for the real send path to run without a
    controller. The certificate material must exist locally, because it is resolved
    before anything is staged. Certificate staging and Authorization-config staging
    must be patched out, because both drive file uploads over SFTP; patching the
    latter is what allows a token to be supplied, which is what lets a test prove the
    token never reaches the command line. The connection must be a non-callable mock,
    because the keyword base class wraps callable attributes in its logging hook, and
    its return code must be pinned to zero, because any other value is read as a
    transport failure.

    Args:
        cert_dir (str): Directory to create the certificate material in.
        send_output (str): Output the mocked connection returns for the request.

    Returns:
        O2RestClient: Client whose ssh_connection is the mock, ready to send.
    """
    _write_empty_file(cert_dir, O2RestClient.CLIENT_CERT_FILE)
    _write_empty_file(cert_dir, O2RestClient.CLIENT_KEY_FILE)
    _write_empty_file(cert_dir, O2RestClient.CA_CERT_FILE)

    mock_ssh = NonCallableMagicMock(spec=SSHConnection)
    mock_ssh.send.return_value = send_output
    mock_ssh.get_return_code.return_value = 0

    # Both the constructor and the send path log, so the logger must be configured.
    ConfigurationManager.load_configs(ConfigurationFileLocationsManager())

    staged_certs = (os.path.join(cert_dir, O2RestClient.CLIENT_CERT_FILE), os.path.join(cert_dir, O2RestClient.CLIENT_KEY_FILE))
    with patch.object(O2RestClient, "_stage_certs_on_controller", return_value=staged_certs), patch("keywords.cloud_platform.rest.oran_o2.o2_rest_client.stage_auth_config", return_value=os.path.join(cert_dir, "auth.cfg")):
        return O2RestClient(cert_dir, ssh_connection=mock_ssh, token=_TEST_TOKEN)


def test_patch_carries_the_method_content_type_and_body():
    """A PATCH names the method and sends the body as JSON."""
    with tempfile.TemporaryDirectory() as temp_dir:
        client = _build_client_with_mock_connection(temp_dir, f"{{}}\n{_STATUS_MARKER}404")

        client.patch(_ALARM_URL, data=_ALARM_BODY)

        command = client.ssh_connection.send.call_args[0][0]
        assert "-X PATCH" in command
        assert "Content-Type: application/json" in command
        assert _ALARM_BODY in command
        assert _ALARM_URL in command


def test_patch_keeps_the_token_and_the_authorization_header_off_the_command_line():
    """A PATCH authenticates by config-file reference, never by an inline header.

    The SSH layer logs every command verbatim, so a token on the command line would
    be written to the log. The token is supplied to the constructor here, so its
    absence from the command is evidence rather than an accident of configuration.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        client = _build_client_with_mock_connection(temp_dir, f"{{}}\n{_STATUS_MARKER}404")

        client.patch(_ALARM_URL, data=_ALARM_BODY)

        command = client.ssh_connection.send.call_args[0][0]
        assert "Authorization" not in command
        assert _TEST_TOKEN not in command
        assert "-K " in command


def test_patch_inherits_the_no_fail_transport_contract():
    """A PATCH returning 404 yields a response carrying that status, not an error.

    curl runs without --fail, so an HTTP error status exits zero and arrives as data
    the caller can assert on. This is what lets the negative tests compare a status
    instead of catching an exception.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        body = '{"detail": "404 Not Found: Alarm Event Record abc doesn\'t exist"}'
        client = _build_client_with_mock_connection(temp_dir, f"{body}\n{_STATUS_MARKER}404")

        response = client.patch(_ALARM_URL, data=_ALARM_BODY)

        command = client.ssh_connection.send.call_args[0][0]
        assert "--fail" not in command
        assert response.get_status_code() == 404
        assert "doesn't exist" in response.get_body()


def test_patch_requires_a_request_body():
    """Omitting the body is a signature error, not a request with no content type.

    The send path attaches the content type and the body argument only when a body is
    present, so a defaulted empty body would send neither and the server would reject
    the request for a reason unrelated to the behaviour under test.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        client = _build_client_with_mock_connection(temp_dir, f"{{}}\n{_STATUS_MARKER}404")

        with pytest.raises(TypeError):
            client.patch(_ALARM_URL)
