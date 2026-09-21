import os
import shlex
import tempfile

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.oran_o2.object.o2_rest_response import O2RestResponse
from keywords.files.file_keywords import FileKeywords

# Sentinel separating the response body from the trailing status code emitted by
# curl's -w option, so a single invocation returns both.
_STATUS_MARKER = "O2_HTTP_STATUS:"

# Directory on the controller where the client certificate material is staged for
# curl. The runner's canonical cert material is uploaded here, so the client does
# not depend on any deployment-internal path or naming.
_REMOTE_CERT_DIR = "/tmp/o2ims_client_certs"

# Curl config files on the controller holding the Authorization header. The token
# is passed to curl through a config file rather than on the command line, because
# the SSH layer logs every command it sends verbatim.
_AUTH_CONFIG_FILE = "auth.cfg"
_AUTH_OVERRIDE_CONFIG_FILE = "auth_override.cfg"

# Curl exit codes seen on this path, mapped to the transport-level cause they
# indicate. Curl runs without --fail, so an HTTP error status still exits 0 and
# is reported as a status code; a non-zero exit means no HTTP response arrived at
# all, which on this path is almost always the certificate material or the route
# to the controller rather than the API.
_CURL_EXIT_CAUSES = {
    6: "the host could not be resolved",
    7: "the connection to the host was refused",
    28: "the operation timed out",
    35: "the TLS handshake failed, which usually means the client certificate was rejected",
    58: "the local client certificate could not be used",
    60: "the server certificate could not be verified against the CA",
    77: "the CA certificate file could not be read",
}

# Canonical client certificate material file names on the runner.
CLIENT_CERT_FILE = "client-cert.pem"
CLIENT_KEY_FILE = "client-key.pem"
CA_CERT_FILE = "my-root-ca-cert.pem"


def stage_auth_config(ssh_connection: SSHConnection, token: str, remote_path: str) -> str:
    """Write the Authorization header to a curl config file on the controller.

    The token reaches the controller inside a file uploaded over SFTP, so it never
    appears in a command string or a log line. A module-level function (not a
    keyword method) so the BaseKeyword logging hook does not debug-log the token
    it receives as an argument.

    Args:
        ssh_connection (SSHConnection): Connection to the controller.
        token (str): Bearer token to write into the config file.
        remote_path (str): Destination path for the config file on the controller.

    Returns:
        str: The remote path of the staged config file.
    """
    local_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".cfg", delete=False) as config_file:
            config_file.write(f'header = "Authorization: Bearer {token}"\n')
            local_path = config_file.name
        FileKeywords(ssh_connection).upload_file(local_path, remote_path, overwrite=True)
        ssh_connection.send(f"chmod 600 {shlex.quote(remote_path)}")
    finally:
        if local_path and os.path.isfile(local_path):
            os.unlink(local_path)
    return remote_path


def load_cert_pair(cert_dir: str) -> tuple[str, str, str]:
    """Resolve the client certificate, key and CA paths, verifying all material is present.

    A module-level function (not a keyword method) so it is not wrapped by the
    BaseKeyword logging hook and can be exercised without a configured logger. The
    files are referenced by path only; their contents are never read, so no key
    body reaches a log.

    Args:
        cert_dir (str): Directory holding the certificate material.

    Returns:
        tuple[str, str, str]: The (client_cert_path, client_key_path, ca_cert_path).

    Raises:
        FileNotFoundError: If any of the three certificate files is absent.
    """
    resolved_dir = os.path.expanduser(cert_dir)
    for file_name in (CLIENT_CERT_FILE, CLIENT_KEY_FILE, CA_CERT_FILE):
        file_path = os.path.join(resolved_dir, file_name)
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Required O2 certificate file '{file_name}' not found in directory '{resolved_dir}'")
    return (
        os.path.join(resolved_dir, CLIENT_CERT_FILE),
        os.path.join(resolved_dir, CLIENT_KEY_FILE),
        os.path.join(resolved_dir, CA_CERT_FILE),
    )


class O2RestClient(BaseKeyword):
    """Client for the O2 IMS API, executed on the controller over SSH.

    The O2 IMS API is a controller-side NodePort with mutual TLS and OAuth2
    Bearer authentication. On a hardened jump-host lab it is not reachable over
    TCP from the test runner (the floating IP NATs only SSH) and the controller
    refuses TCP forwarding, so the request is executed on the controller with
    `curl` presenting the client certificate, over the active-controller SSH
    connection.

    The client certificate material is staged on the controller from the runner's
    canonical certificate directory at construction, so the client depends only on
    the runner-side contract (client-cert.pem, client-key.pem, my-root-ca-cert.pem)
    and not on any deployment-internal path. This mirrors the on-controller mTLS curl
    mechanism of `CurlMtlsKeywords`, but adds the OAuth2 `Authorization: Bearer`
    header (which `CurlMtlsKeywords` does not support) and returns both the status
    code and the body from a single invocation. Server verification is skipped
    (`curl -k`) because the server certificate cannot be verified against the
    address dialed, while the client certificate is still presented for mutual TLS.

    The Bearer token is supplied to curl through a config file staged on the
    controller over SFTP, not on the command line, because the SSH layer logs every
    command verbatim. Requests therefore carry only the config file path, keeping
    the token out of log lines, command strings and debug-logged arguments.
    """

    CLIENT_CERT_FILE = CLIENT_CERT_FILE
    CLIENT_KEY_FILE = CLIENT_KEY_FILE
    CA_CERT_FILE = CA_CERT_FILE

    def __init__(self, cert_dir: str, ssh_connection: SSHConnection, token: str = None):
        """Constructor.

        Args:
            cert_dir (str): Directory on the runner holding the client certificate
                material (client-cert.pem, client-key.pem, my-root-ca-cert.pem).
                A leading '~' is expanded.
            ssh_connection (SSHConnection): Active-controller SSH connection that
                runs curl against the controller-side O2 API.
            token (str): OAuth2 Bearer token to attach to authenticated requests.
                Defaults to None, in which case only the no-auth method is usable.

        Raises:
            FileNotFoundError: If any of the three certificate files is absent from cert_dir.
        """
        local_cert, local_key, _ = load_cert_pair(cert_dir)
        self.ssh_connection = ssh_connection
        self.auth_config_path = None
        # A None connection validates the certificate material only: nothing is
        # staged on the controller, so no request can be sent through this client.
        if ssh_connection is not None:
            self.remote_cert_path, self.remote_key_path = self._stage_certs_on_controller(local_cert, local_key)
            if token:
                self.auth_config_path = stage_auth_config(ssh_connection, token, f"{_REMOTE_CERT_DIR}/{_AUTH_CONFIG_FILE}")
                get_logger().log_info(f"Staged O2 Bearer token ({len(token)} chars) in a curl config on the controller")

    def _stage_certs_on_controller(self, local_cert: str, local_key: str) -> tuple[str, str]:
        """Upload the client certificate and key to the controller for curl to use.

        Args:
            local_cert (str): Path to the client certificate on the runner.
            local_key (str): Path to the client key on the runner.

        Returns:
            tuple[str, str]: The (remote_cert_path, remote_key_path) on the controller.
        """
        file_keywords = FileKeywords(self.ssh_connection)
        remote_cert_path = f"{_REMOTE_CERT_DIR}/{self.CLIENT_CERT_FILE}"
        remote_key_path = f"{_REMOTE_CERT_DIR}/{self.CLIENT_KEY_FILE}"
        file_keywords.create_directory(_REMOTE_CERT_DIR)
        file_keywords.upload_file(local_cert, remote_cert_path, overwrite=True)
        file_keywords.upload_file(local_key, remote_key_path, overwrite=True)
        return (remote_cert_path, remote_key_path)

    def get(self, url: str) -> O2RestResponse:
        """Run an authenticated GET on the controller, presenting the client cert and Bearer token.

        Args:
            url (str): The URL to GET.

        Returns:
            O2RestResponse: Response exposing the HTTP status code and JSON body.
        """
        return self._send("GET", url, auth_config_path=self.auth_config_path)

    def delete(self, url: str) -> O2RestResponse:
        """Run an authenticated DELETE on the controller.

        Args:
            url (str): The URL to DELETE.

        Returns:
            O2RestResponse: Response exposing the HTTP status code and JSON body.
        """
        return self._send("DELETE", url, auth_config_path=self.auth_config_path)

    def post(self, url: str, data: str = "") -> O2RestResponse:
        """Run an authenticated POST on the controller.

        Args:
            url (str): The URL to POST to.
            data (str): The request body. Defaults to "".

        Returns:
            O2RestResponse: Response exposing the HTTP status code and JSON body.
        """
        return self._send("POST", url, auth_config_path=self.auth_config_path, data=data)

    def get_no_auth(self, url: str) -> O2RestResponse:
        """Run a GET on the controller with no Authorization header, still presenting the client cert.

        Args:
            url (str): The URL to GET.

        Returns:
            O2RestResponse: Response exposing the HTTP status code and JSON body.
        """
        return self._send("GET", url, auth_config_path=None)

    def get_with_token(self, url: str, token: str) -> O2RestResponse:
        """Run a GET on the controller with a caller-supplied Bearer token.

        Exercises token validation with a specific token without disturbing the
        client's configured token. The supplied value is a keyword argument and is
        therefore debug-logged, so do not pass a real credential here.

        Args:
            url (str): The URL to GET.
            token (str): The Bearer token to present.

        Returns:
            O2RestResponse: Response exposing the HTTP status code and JSON body.
        """
        override_path = stage_auth_config(self.ssh_connection, token, f"{_REMOTE_CERT_DIR}/{_AUTH_OVERRIDE_CONFIG_FILE}")
        return self._send("GET", url, auth_config_path=override_path)

    def _send(self, method: str, url: str, auth_config_path: str = None, data: str = "") -> O2RestResponse:
        """Execute an mTLS curl on the controller and build the response.

        A single curl invocation returns the body followed by the status code via
        curl's -w option. The Authorization header is supplied through a curl
        config file, so the token never appears in the command string the SSH layer
        logs, nor in the arguments this method is called with.

        Curl runs without --fail, so an HTTP error status exits 0 and is returned
        as a status code for the caller to assert on. A non-zero exit means no
        HTTP response arrived, so this raises naming the method, the URL, the curl
        exit code and its likely cause rather than surfacing a bare return code.

        Args:
            method (str): HTTP method.
            url (str): The URL.
            auth_config_path (str): Path on the controller to a curl config file
                holding the Authorization header, or None for no authentication.
            data (str): Request body. Defaults to "".

        Returns:
            O2RestResponse: Response exposing the HTTP status code and JSON body.

        Raises:
            KeywordException: If curl exited non-zero, meaning no HTTP response arrived.
        """
        parts = [
            "curl -s -k",
            f"--cert {shlex.quote(self.remote_cert_path)}",
            f"--key {shlex.quote(self.remote_key_path)}",
            f"-X {shlex.quote(method)}",
        ]
        if auth_config_path:
            parts.append(f"-K {shlex.quote(auth_config_path)}")
        if data:
            parts.append("-H " + shlex.quote("Content-Type: application/json"))
            parts.append(f"-d {shlex.quote(data)}")
        parts.append(f"-w {shlex.quote(chr(10) + _STATUS_MARKER + '%{http_code}')}")
        parts.append(shlex.quote(url))
        cmd = " ".join(parts)

        output = self.ssh_connection.send(cmd)
        return_code = self.ssh_connection.get_return_code()
        if return_code is not None and return_code != 0:
            cause = _CURL_EXIT_CAUSES.get(return_code, "curl reported a transport-level failure")
            raise KeywordException(f"O2 {method} {url} received no HTTP response: curl exited {return_code} because {cause}. The client certificate staged on the controller is '{self.remote_cert_path}' with key '{self.remote_key_path}'. If the certificate material is stale, regenerate it.")
        status_code, body = self._split_body_and_status(output)
        get_logger().log_info(f"O2 {method} {url} -> HTTP {status_code}")
        return O2RestResponse(status_code, body)

    @staticmethod
    def _split_body_and_status(output: str | list) -> tuple[int, str]:
        """Split curl output into the JSON body and the trailing status code.

        Args:
            output (str | list): Raw curl output ending with the status marker.

        Returns:
            tuple[int, str]: The (status_code, body) pair.
        """
        text = "\n".join(output) if isinstance(output, list) else output
        marker_index = text.rfind(_STATUS_MARKER)
        if marker_index == -1:
            return (0, text.strip())
        body = text[:marker_index].strip()
        status_text = text[marker_index + len(_STATUS_MARKER) :].strip()
        status_code = int(status_text) if status_text.isdigit() else 0
        return (status_code, body)
