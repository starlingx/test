"""Output parser for system certificate-show command."""

from keywords.cloud_platform.system.certificate.objects.system_certificate_show_object import SystemCertificateShowObject


class SystemCertificateShowOutput:
    """Parses the output of 'system certificate-show <cert-name>'.

    Sample output:
        Certificate:
           Residual Time: 87d
           Version: v3
           Serial Number: 0x7d23fbbb...
           Issuer: CN=starlingx
           Validity:
              Not Before: July 19 07:20:49 2026
              Not After: October 17 07:20:49 2026
           Subject: CN=engineering.com,OU=testing,...
           Subject Public Key Info:
              key_size: (384 bit)
           Signature Algorithm: ecdsa-with-SHA384
           File Path: /etc/ssl/private/server-cert.pem
           Renewal: Automatic
           Namespace: deployment
           Secret: system-restapi-gui-certificate
    """

    def __init__(self, raw_output: str) -> None:
        """Constructor.

        Args:
            raw_output (str): Raw output from system certificate-show command.
        """
        self.cert_show_object = self._parse(raw_output)

    def get_certificate_show(self) -> SystemCertificateShowObject:
        """Get the parsed certificate show object.

        Returns:
            SystemCertificateShowObject: Parsed certificate details.
        """
        return self.cert_show_object

    def _parse(self, raw: str) -> SystemCertificateShowObject:
        """Parse system certificate-show output.

        Args:
            raw (str): Raw command output.

        Returns:
            SystemCertificateShowObject: Parsed object with all certificate fields.
        """
        obj = SystemCertificateShowObject()
        lines = raw.split("\n") if isinstance(raw, str) else raw

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("Residual Time:"):
                obj.set_residual_time(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("Version:"):
                obj.set_version(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("Serial Number:"):
                obj.set_serial_number(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("Issuer:"):
                obj.set_issuer(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("Not Before:"):
                obj.set_not_before(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("Not After:"):
                obj.set_not_after(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("Subject:") and "Public Key" not in stripped:
                obj.set_subject(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("key_size:"):
                obj.set_key_size(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("Signature Algorithm:"):
                obj.set_signature_algorithm(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("File Path:"):
                obj.set_file_path(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("Renewal:"):
                obj.set_renewal(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("Namespace:"):
                obj.set_namespace(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("Secret:"):
                obj.set_secret(stripped.split(":", 1)[1].strip())

        return obj
