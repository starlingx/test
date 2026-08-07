"""OpenSSLKeywords keywords."""

from datetime import datetime, timezone

from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords
from keywords.openssl.object.cert_key_info_object import CertKeyInfoObject
from keywords.openssl.object.cert_key_info_output import CertKeyInfoOutput
from keywords.openssl.objects.certificate_info_object import CertificateInfoObject
from keywords.openssl.objects.certificate_info_output import CertificateInfoOutput


class OpenSSLKeywords(BaseKeyword):
    """Keyword library for OpenSSL operations such as certificate inspection and decoding.

    This class provides utility methods for interacting with OpenSSL in the context of
    Kubernetes TLS certificate validation.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize OpenSSLKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def get_cert_key_info_from_secret(self, secret_name: str, namespace: str) -> CertKeyInfoObject:
        """Extract key algorithm information from a Kubernetes TLS secret.

        Uses KubectlGetSecretsKeywords to extract cert data, then parses with openssl.

        Args:
            secret_name (str): Name of the Kubernetes secret.
            namespace (str): Namespace where the secret resides.

        Returns:
            CertKeyInfoObject: Object with key type, curve, and size.
        """
        secrets_kw = KubectlGetSecretsKeywords(self.ssh_connection)
        cert_pem = secrets_kw.get_secret_with_custom_output(secret_name, namespace, "go-template", "'{{index .data \"tls.crt\"}}'", base64=True)
        file_kw = FileKeywords(self.ssh_connection)
        file_kw.create_file_with_echo("/tmp/_cert_inspect.pem", cert_pem)

        output = self.ssh_connection.send("openssl x509 -in /tmp/_cert_inspect.pem -noout -text")
        self.validate_success_return_code(self.ssh_connection)
        file_kw.delete_file("/tmp/_cert_inspect.pem")

        raw = "\n".join(output) if isinstance(output, list) else output
        return CertKeyInfoOutput(raw).get_cert_key_info()

    def get_cert_key_info_from_file(self, cert_path: str) -> CertKeyInfoObject:
        """Extract key algorithm information from a certificate file on the host.

        Args:
            cert_path (str): Absolute path to the PEM certificate file.

        Returns:
            CertKeyInfoObject: Object with key type, curve, and size.
        """
        output = self.ssh_connection.send_as_sudo(f"openssl x509 -in {cert_path} -noout -text")
        self.validate_success_return_code(self.ssh_connection)
        raw = "\n".join(output) if isinstance(output, list) else output
        return CertKeyInfoOutput(raw).get_cert_key_info()

    def parse_cert_key_info(self, cert_text: str) -> CertKeyInfoObject:
        """Parse certificate text output to extract key algorithm information.

        Args:
            cert_text (str): Raw output from openssl x509 -text.

        Returns:
            CertKeyInfoObject: Object with key type, curve, and size.

        Raises:
            KeywordException: If key type cannot be determined.
        """
        result = CertKeyInfoOutput(cert_text).get_cert_key_info()
        if not result.get_type():
            raise KeywordException(f"Unable to determine key type from certificate output: {cert_text[:500]}")
        return result

    def verify_cert_chain(self, trusted_ca_path: str, untrusted_ica_path: str, cert_path: str) -> None:
        """Verify a certificate chain using openssl verify.

        Args:
            trusted_ca_path (str): Path to the trusted root CA PEM file.
            untrusted_ica_path (str): Path to the untrusted intermediate CA PEM file.
            cert_path (str): Path to the certificate to verify.

        Raises:
            KeywordException: If chain verification fails.
        """
        output = self.ssh_connection.send_as_sudo(f"openssl verify -trusted {trusted_ca_path} -untrusted {untrusted_ica_path} {cert_path}")
        self.validate_success_return_code(self.ssh_connection)
        raw = "\n".join(output) if isinstance(output, list) else output
        if "OK" not in raw:
            raise KeywordException(f"Certificate chain verification failed for {cert_path}: {raw}")

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

    def create_certificate_signing_request(self, key_path: str, csr_path: str, subj: str, san: str = "") -> None:
        """Create a certificate signing request (CSR).

        Args:
            key_path (str): Path to the private key.
            csr_path (str): Path to write the CSR.
            subj (str): Certificate subject string.
            san (str): Subject Alternative Name extension value
                (e.g. "DNS:example.com"). If empty, no SAN is added.
        """
        san_opt = f" -addext \"subjectAltName={san}\"" if san else ""
        self.ssh_connection.send(f'openssl req -new -key {key_path} -out {csr_path} -subj "{subj}"{san_opt}')
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
            dict: Dictionary with keys 'not_before' (datetime), 'not_after' (datetime), and 'serial' (str).
        """
        output = self.ssh_connection.send_as_sudo(f"openssl x509 -in {cert_path} -noout -dates -serial")
        self.validate_success_return_code(self.ssh_connection)
        raw = "\n".join(output) if isinstance(output, list) else output
        result = {}
        for line in raw.splitlines():
            if line.startswith("notBefore="):
                result["not_before"] = self._parse_openssl_date(line.split("=", 1)[1].strip())
            elif line.startswith("notAfter="):
                result["not_after"] = self._parse_openssl_date(line.split("=", 1)[1].strip())
            elif line.startswith("serial="):
                result["serial"] = line.split("=", 1)[1].strip()
        return result

    def get_certificate_info(self, cert_path: str) -> CertificateInfoObject:
        """Get subject, issuer, and serial from a certificate file in one call.

        Args:
            cert_path (str): Path to the certificate file.

        Returns:
            CertificateInfoObject: Object with get_subject(), get_issuer(), get_serial().
        """
        output = self.ssh_connection.send(f"openssl x509 -in {cert_path} -noout -subject -issuer -serial")
        self.validate_success_return_code(self.ssh_connection)
        return CertificateInfoOutput(output).get_certificate_info()

    def check_cert_expiry(self, cert_path: str, seconds: int = 2592000) -> bool:
        """Check if a certificate expires within the given time window.

        Args:
            cert_path (str): Path to the PEM certificate file.
            seconds (int): Time window in seconds (default 30 days = 2592000).

        Returns:
            bool: True if certificate is still valid beyond the window, False if expiring.
        """
        output = self.ssh_connection.send(f"openssl x509 -in {cert_path} -checkend {seconds} -noout > /dev/null 2>&1 && echo VALID || echo EXPIRING")
        raw = "\n".join(output) if isinstance(output, list) else output
        return "VALID" in raw

    def generate_self_signed_cert(self, key_path: str, cert_path: str, subj: str, days: int = 1, algorithm: str = "ECDSA", curve: str = "secp384r1", rsa_size: int = 4096) -> None:
        """Generate a self-signed certificate with specified key type.

        Args:
            key_path (str): Path to write the private key.
            cert_path (str): Path to write the certificate.
            subj (str): Certificate subject string.
            days (int): Validity in days. Defaults to 1.
            algorithm (str): Key algorithm ("ECDSA" or "RSA"). Defaults to "ECDSA".
            curve (str): ECDSA curve name. Defaults to "secp384r1".
            rsa_size (int): RSA key size. Defaults to 4096.
        """
        if algorithm == "ECDSA":
            cmd = f"openssl req -x509 -nodes -newkey ec -pkeyopt ec_paramgen_curve:{curve} -keyout {key_path} -out {cert_path} -days {days} -subj '{subj}'"
        else:
            cmd = f"openssl req -x509 -nodes -newkey rsa:{rsa_size} -keyout {key_path} -out {cert_path} -days {days} -subj '{subj}'"
        self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)

    def get_cert_text_from_file(self, cert_path: str) -> str:
        """Get full openssl x509 -text output from a certificate file.

        Args:
            cert_path (str): Path to the PEM certificate file.

        Returns:
            str: Full openssl x509 -noout -text output.
        """
        output = self.ssh_connection.send(f"openssl x509 -in {cert_path} -noout -text")
        self.validate_success_return_code(self.ssh_connection)
        return "\n".join(output) if isinstance(output, list) else output

    @staticmethod
    def _parse_openssl_date(date_str: str) -> datetime:
        """Parse OpenSSL date string to a timezone-aware datetime.

        Args:
            date_str (str): OpenSSL date format (e.g., 'Sep 29 04:34:00 2026 GMT').

        Returns:
            datetime: Parsed datetime object with UTC timezone.
        """
        return datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)

    def get_cert_key_info_from_kubeconfig(self, kubeconfig_path: str) -> "CertKeyInfoObject":
        """Extract client certificate key info from a kubeconfig file.

        Reads the kubeconfig, extracts client-certificate-data, decodes it,
        and parses the certificate key type information.

        Args:
            kubeconfig_path (str): Path to the kubeconfig file.

        Returns:
            CertKeyInfoObject: Parsed key info from the embedded client certificate.
        """
        import base64 as b64

        from keywords.files.file_keywords import FileKeywords

        file_kw = FileKeywords(self.ssh_connection)
        conf_content = file_kw.read_file_with_sudo(kubeconfig_path)
        cert_b64_line = ""
        for line in conf_content:
            if "client-certificate-data" in line:
                cert_b64_line = line.strip().split()[-1]
                break
        cert_pem = b64.b64decode(cert_b64_line).decode("utf-8")
        file_kw.create_file_with_heredoc("/tmp/_kubeconfig_cert.pem", cert_pem)
        raw = self.get_cert_text_from_file("/tmp/_kubeconfig_cert.pem")
        file_kw.delete_file("/tmp/_kubeconfig_cert.pem")
        return self.parse_cert_key_info(raw)
