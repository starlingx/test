from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.security.ejbca.objects.revocation_reason import RevocationReason
from keywords.openssl.objects.certificate_info_object import CertificateInfoObject
from keywords.openssl.openssl_keywords import OpenSSLKeywords


class EjbcaCmpKeywords(BaseKeyword):
    """Keywords for EJBCA CMPv2 certificate operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize CMP keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the system.
        """
        self.ssh_connection = ssh_connection
        self.openssl_keywords = OpenSSLKeywords(ssh_connection)

    def generate_key_and_csr(self, cn: str, key_path: str, csr_path: str, san_dns: str = "") -> None:
        """Generate an RSA key and CSR with optional SAN extension.

        Args:
            cn (str): Common Name for the certificate subject.
            key_path (str): Path to write the private key.
            csr_path (str): Path to write the CSR.
            san_dns (str): DNS SAN value. If empty, no SAN is added.
        """
        self.openssl_keywords.generate_rsa_key(key_path)
        san = f"DNS:{san_dns}" if san_dns else ""
        self.openssl_keywords.create_certificate_signing_request(
            key_path, csr_path, f"/CN={cn}", san=san
        )

    def cmp_enroll(self, server: str, path: str, hmac_secret: str, cn: str, key_path: str, csr_path: str, cert_out: str, ca_cert_out: str = "", tls_trusted: str = "") -> str:
        """Enroll a certificate via CMP initial request.

        Args:
            server (str): CMP server address (host:port).
            path (str): CMP URL path.
            hmac_secret (str): HMAC shared secret for authentication.
            cn (str): Subject CN for the request.
            key_path (str): Path to the private key file.
            csr_path (str): Path to the CSR file.
            cert_out (str): Path to write the issued certificate.
            ca_cert_out (str): Path to write the CA certificate chain.
            tls_trusted (str): Path to trusted CA cert for TLS verification.

        Returns:
            str: Command output from openssl cmp.
        """
        ca_opt = f" -cacertsout {ca_cert_out}" if ca_cert_out else ""
        tls_trust_opt = f" -tls_trusted {tls_trusted}" if tls_trusted else ""
        cmd = (
            f"openssl cmp -server {server} -path {path} -tls_used"
            f"{tls_trust_opt} -cmd ir -secret pass:{hmac_secret}"
            f' -subject "/CN={cn}" -newkey {key_path} -csr {csr_path}'
            f" -certout {cert_out}{ca_opt}"
        )
        get_logger().log_info(f"CMP enrollment for CN={cn}")
        output = self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return "\n".join(output) if isinstance(output, list) else output

    def cmp_revoke(self, server: str, path: str, hmac_secret: str, cn: str, old_cert: str, reason: RevocationReason = RevocationReason.UNSPECIFIED, tls_trusted: str = "") -> str:
        """Revoke a certificate via CMP revocation request.

        Args:
            server (str): CMP server address (host:port).
            path (str): CMP URL path.
            hmac_secret (str): HMAC shared secret for authentication.
            cn (str): Subject CN of the certificate to revoke.
            old_cert (str): Path to the certificate file to revoke.
            reason (RevocationReason): Revocation reason code.
            tls_trusted (str): Path to trusted CA cert for TLS verification.

        Returns:
            str: Command output from openssl cmp.
        """
        tls_trust_opt = f" -tls_trusted {tls_trusted}" if tls_trusted else ""
        cmd = (
            f"openssl cmp -server {server} -path {path} -tls_used"
            f"{tls_trust_opt} -cmd rr -secret pass:{hmac_secret}"
            f' -subject "/CN={cn}" -oldcert {old_cert} -revreason {reason.value}'
        )
        get_logger().log_info(f"CMP revocation for CN={cn}")
        output = self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return "\n".join(output) if isinstance(output, list) else output

    def cmp_enroll_with_invalid_secret(self, server: str, path: str, invalid_secret: str, cn: str, key_path: str, csr_path: str, cert_out: str) -> str:
        """Attempt CMP enrollment with an invalid HMAC secret.

        Does NOT validate return code (expects failure).

        Args:
            server (str): CMP server address (host:port).
            path (str): CMP URL path.
            invalid_secret (str): Incorrect HMAC secret.
            cn (str): Subject CN for the request.
            key_path (str): Path to the private key file.
            csr_path (str): Path to the CSR file.
            cert_out (str): Path where cert would be written.

        Returns:
            str: Command output (expected to contain error message).
        """
        cmd = (
            f"openssl cmp -server {server} -path {path} -tls_used"
            f" -cmd ir -secret pass:{invalid_secret}"
            f' -subject "/CN={cn}" -newkey {key_path} -csr {csr_path}'
            f" -certout {cert_out}"
        )
        get_logger().log_info(f"CMP enrollment with invalid secret for CN={cn}")
        output = self.ssh_connection.send(cmd)
        return "\n".join(output) if isinstance(output, list) else output

    def get_certificate_info(self, cert_path: str) -> CertificateInfoObject:
        """Get subject, issuer, and serial from a certificate file.

        Delegates to OpenSSLKeywords.get_certificate_info for a single
        openssl x509 call returning a structured object.

        Args:
            cert_path (str): Path to the certificate file.

        Returns:
            CertificateInfoObject: Object with get_subject(), get_issuer(), get_serial().
        """
        return self.openssl_keywords.get_certificate_info(cert_path)

    def verify_cert_chain(self, cert_path: str, ca_cert_path: str) -> bool:
        """Verify a certificate against its CA chain.

        Args:
            cert_path (str): Path to the certificate to verify.
            ca_cert_path (str): Path to the CA certificate.

        Returns:
            bool: True if verification succeeds.
        """
        output = self.ssh_connection.send(f"openssl verify -CAfile {ca_cert_path} {cert_path}")
        raw = "\n".join(output) if isinstance(output, list) else output
        rc = self.ssh_connection.get_return_code()
        return rc == 0 and "OK" in raw
