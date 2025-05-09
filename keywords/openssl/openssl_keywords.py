from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class OpenSSLKeywords(BaseKeyword):
    """Keyword library for OpenSSL operations such as certificate inspection and decoding.

    This class provides utility methods for interacting with OpenSSL in the context of
    Kubernetes TLS certificate validation.
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def create_certificate(self, key: str = None, crt: str = None, sys_domain_name: str = None) -> None:
        """
        Creates an SSL certificate file for the Kubernetes dashboard secret.

        Args:
            key (str): The path to the key file.
            crt (str): The path to the certificate file.
            sys_domain_name (str): The system domain name to be used in the certificate.
        """
        args = ""
        if key:
            args += f"-keyout {key} "
        if crt:
            args += f"-out {crt} "
        if sys_domain_name:
            args += f'-subj "/CN={sys_domain_name}"'
        self.ssh_connection.send(f"openssl req -x509 -nodes -days 365 -newkey rsa:2048 {args}")
        self.validate_success_return_code(self.ssh_connection)

    def create_ingress_certificate(self, key: str, crt: str, host: str) -> None:
        """
        Creates an SSL certificate file suitable for Kubernetes Ingress TLS secrets, including Subject Alternative Name.

        Args:
            key (str): The path to the key file.
            crt (str): The path to the certificate file.
            host (str): The hostname that the certificate should be valid for (will be used in SAN).
        """
        command = f"openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout {key} -out {crt} -subj '/CN={host}' -addext 'subjectAltName = DNS:{host}'"
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
