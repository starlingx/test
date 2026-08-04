import json

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.network.curl_mtls_keywords import CurlMtlsKeywords


class EjbcaRestKeywords(BaseKeyword):
    """Keywords for EJBCA REST API certificate operations."""

    def __init__(self, ssh_connection: SSHConnection, admin_cert_path: str, admin_key_path: str):
        """Initialize EJBCA REST keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host.
            admin_cert_path (str): Path to SuperAdmin client certificate.
            admin_key_path (str): Path to SuperAdmin client private key.
        """
        self.ssh_connection = ssh_connection
        self.curl_mtls = CurlMtlsKeywords(ssh_connection, admin_cert_path, admin_key_path)

    def rest_enroll_pkcs10(self, base_url: str, csr_base64: str, cert_profile: str, ee_profile: str, ca_name: str, username: str, password: str) -> dict:
        """Enroll a certificate via REST pkcs10enroll endpoint.

        Args:
            base_url (str): REST API base URL.
            csr_base64 (str): Base64-encoded DER CSR.
            cert_profile (str): Certificate profile name.
            ee_profile (str): End entity profile name.
            ca_name (str): Certificate Authority name.
            username (str): End entity username.
            password (str): Enrollment password.

        Returns:
            dict: JSON response containing the issued certificate.
        """
        payload = json.dumps(
            {
                "certificate_request": csr_base64,
                "certificate_profile_name": cert_profile,
                "end_entity_profile_name": ee_profile,
                "certificate_authority_name": ca_name,
                "username": username,
                "password": password,
                "include_chain": True,
            }
        )
        get_logger().log_info(f"REST enrollment for username={username}")
        output = self.curl_mtls.send_request(
            f"{base_url}/v1/certificate/pkcs10enroll", method="POST", data=payload
        )
        return self._parse_json_response(output)

    def rest_revoke_cert(self, base_url: str, issuer_dn_encoded: str, serial_hex: str, reason: str = "UNSPECIFIED") -> str:
        """Revoke a certificate via REST API.

        Args:
            base_url (str): REST API base URL.
            issuer_dn_encoded (str): URL-encoded issuer DN.
            serial_hex (str): Certificate serial number in hex.
            reason (str): Revocation reason string.

        Returns:
            str: Response from the revocation endpoint.
        """
        url = f"{base_url}/v1/certificate/{issuer_dn_encoded}/{serial_hex}/revoke?reason={reason}"
        get_logger().log_info(f"REST revocation for serial={serial_hex}")
        return self.curl_mtls.send_request(url, method="PUT")

    def rest_get_revocation_status(self, base_url: str, issuer_dn_encoded: str, serial_hex: str) -> dict:
        """Get revocation status of a certificate via REST API.

        Args:
            base_url (str): REST API base URL.
            issuer_dn_encoded (str): URL-encoded issuer DN.
            serial_hex (str): Certificate serial number in hex.

        Returns:
            dict: JSON response with revocation status.
        """
        url = f"{base_url}/v1/certificate/{issuer_dn_encoded}/{serial_hex}/revocationstatus"
        output = self.curl_mtls.send_request(url)
        return self._parse_json_response(output)

    def rest_list_cas(self, base_url: str) -> dict:
        """List all CAs via REST API.

        Args:
            base_url (str): REST API base URL.

        Returns:
            dict: JSON response with CA listing.
        """
        output = self.curl_mtls.send_request(f"{base_url}/v1/ca")
        return self._parse_json_response(output)

    def rest_no_client_cert_rejected(self, url: str) -> int:
        """Verify REST endpoint rejects requests without client cert.

        Args:
            url (str): Full URL to test.

        Returns:
            int: HTTP return code (expected non-zero).
        """
        cmd = f'curl -sk -H "Accept: application/json" {url}'
        self.ssh_connection.send(cmd)
        return self.ssh_connection.get_return_code()

    def generate_csr_der_base64(self, key_path: str, csr_der_path: str, cn: str) -> str:
        """Generate a CSR in DER format and return its base64 encoding.

        Args:
            key_path (str): Path to the private key.
            csr_der_path (str): Path to write the DER-encoded CSR.
            cn (str): Common Name for the subject.

        Returns:
            str: Base64-encoded DER CSR string.
        """
        cmd = f'openssl req -new -key {key_path} -subj "/CN={cn}" -outform DER -out {csr_der_path}'
        self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)
        output = self.ssh_connection.send(f"base64 -w0 {csr_der_path}")
        self.validate_success_return_code(self.ssh_connection)
        raw = "\n".join(output) if isinstance(output, list) else output
        return raw.strip()

    def _parse_json_response(self, output) -> dict:
        """Parse JSON from curl output.

        Args:
            output: Raw curl output (str or list).

        Returns:
            dict: Parsed JSON response, or empty dict on failure.
        """
        raw = "\n".join(output) if isinstance(output, list) else output
        lines = raw.strip().splitlines()
        json_str = ""
        for line in lines:
            if line.strip().startswith("{") or line.strip().startswith("["):
                json_str = "\n".join(lines[lines.index(line):])
                break
        if not json_str:
            json_str = raw.strip()
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            get_logger().log_error(f"Failed to parse JSON: {raw[:200]}")
            return {}
