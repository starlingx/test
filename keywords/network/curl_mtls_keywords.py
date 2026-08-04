from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class CurlMtlsKeywords(BaseKeyword):
    """Keywords for performing mTLS-authenticated HTTP requests via curl.

    Provides a reusable curl wrapper that sends requests with a client
    certificate and private key for mutual TLS authentication. Suitable
    for any REST API that requires certificate-based client identity.
    """

    def __init__(self, ssh_connection: SSHConnection, client_cert_path: str, client_key_path: str):
        """Initialize mTLS curl keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host that will run curl.
            client_cert_path (str): Path to the client certificate file (PEM).
            client_key_path (str): Path to the client private key file (PEM).
        """
        self.ssh_connection = ssh_connection
        self.client_cert_path = client_cert_path
        self.client_key_path = client_key_path

    def send_request(self, url: str, method: str = "GET", data: str = "", content_type: str = "application/json", accept: str = "application/json", verify_ssl: bool = False) -> str:
        """Send an mTLS-authenticated HTTP request via curl.

        Args:
            url (str): Full URL to send the request to.
            method (str): HTTP method (GET, POST, PUT, DELETE, PATCH).
            data (str): Request body (typically JSON string).
            content_type (str): Content-Type header value.
            accept (str): Accept header value.
            verify_ssl (bool): If False, use -k to skip server cert verification.

        Returns:
            str: Response body from the server.
        """
        insecure = " -k" if not verify_ssl else ""
        data_opt = f" -d '{data}'" if data else ""
        method_opt = f" -X {method}" if method != "GET" else ""
        cmd = (
            f"curl -s{insecure}"
            f" --cert {self.client_cert_path}"
            f" --key {self.client_key_path}"
            f' -H "Content-Type: {content_type}"'
            f' -H "Accept: {accept}"'
            f"{method_opt} {url}{data_opt}"
        )
        get_logger().log_info(f"mTLS {method} {url}")
        output = self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return output

    def get_http_status_code(self, url: str, verify_ssl: bool = False) -> str:
        """Send an mTLS GET and return only the HTTP status code.

        Args:
            url (str): Full URL to query.
            verify_ssl (bool): If False, use -k to skip server cert verification.

        Returns:
            str: HTTP status code as a string (e.g. "200", "401").
        """
        insecure = " -k" if not verify_ssl else ""
        cmd = (
            f"curl -s{insecure} -o /dev/null -w '%{{http_code}}'"
            f" --cert {self.client_cert_path}"
            f" --key {self.client_key_path}"
            f" {url}"
        )
        output = self.ssh_connection.send(cmd)
        raw = "\n".join(output) if isinstance(output, list) else output
        return raw.strip()
