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

    def generate_rsa_key(self, key_path: str, bits: int = 2048) -> None:
        """Generate an RSA private key.

        Args:
            key_path (str): Path to write the generated key.
            bits (int): Key size in bits. Defaults to 2048.
        """
        self.ssh_connection.send(f"openssl genrsa -out {key_path} {bits}")
        self.validate_success_return_code(self.ssh_connection)

    def create_self_signed_ca_certificate(self, key_path: str, cert_path: str, subj: str, days: int = 1024) -> None:
        """Create a self-signed CA certificate.

        Args:
            key_path (str): Path to the CA private key.
            cert_path (str): Path to write the CA certificate.
            subj (str): Certificate subject string.
            days (int): Certificate validity in days. Defaults to 1024.
        """
        self.ssh_connection.send(f"openssl req -x509 -new -nodes -key {key_path} -days {days} " f'-out {cert_path} -outform PEM -subj "{subj}"')
        self.validate_success_return_code(self.ssh_connection)

    def create_certificate_signing_request(self, key_path: str, csr_path: str, subj: str) -> None:
        """Create a certificate signing request (CSR).

        Args:
            key_path (str): Path to the private key.
            csr_path (str): Path to write the CSR.
            subj (str): Certificate subject string.
        """
        self.ssh_connection.send(f'openssl req -new -key {key_path} -out {csr_path} -subj "{subj}"')
        self.validate_success_return_code(self.ssh_connection)

    def sign_certificate(self, csr_path: str, ca_cert_path: str, ca_key_path: str, cert_path: str, days: int = 365) -> None:
        """Sign a certificate with a CA.

        Args:
            csr_path (str): Path to the CSR.
            ca_cert_path (str): Path to the CA certificate.
            ca_key_path (str): Path to the CA private key.
            cert_path (str): Path to write the signed certificate.
            days (int): Certificate validity in days. Defaults to 365.
        """
        self.ssh_connection.send(f"openssl x509 -req -in {csr_path} -CA {ca_cert_path} " f"-CAkey {ca_key_path} -CAcreateserial -out {cert_path} -days {days}")
        self.validate_success_return_code(self.ssh_connection)

    def get_cert_info_from_file(self, cert_path: str) -> dict:
        """Read certificate dates and serial number from a PEM file on the remote host.

        Args:
            cert_path (str): Absolute path to the PEM certificate file on the remote host.

        Returns:
            dict: Dictionary with keys 'not_before', 'not_after', and 'serial'.
        """
        output = self.ssh_connection.send_as_sudo(f"openssl x509 -in {cert_path} -noout -dates -serial")
        self.validate_success_return_code(self.ssh_connection)
        raw = "\n".join(output) if isinstance(output, list) else output
        result = {}
        for line in raw.splitlines():
            if line.startswith("notBefore="):
                result["not_before"] = line.split("=", 1)[1].strip()
            elif line.startswith("notAfter="):
                result["not_after"] = line.split("=", 1)[1].strip()
            elif line.startswith("serial="):
                result["serial"] = line.split("=", 1)[1].strip()
        return result
