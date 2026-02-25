import base64

from keywords.cloud_platform.security.cat.objects.ssl_ca_certificate_object import SslCaCertificateObject


class SslCaCertificateOutput:
    """
    Output class for parsing SSL CA certificate command output.
    """

    def __init__(self, command_output: list, ssl_ca_dir: str, ca_file_name: str):
        """
        Constructor.

        Create an internal SslCaCertificateObject.

        Args:
            command_output (list): Raw command output lines from cat command
            ssl_ca_dir (str): SSL CA directory path
            ca_file_name (str): Certificate file name
        """
        # Remove last line (shell prompt) and join certificate content
        cert_text = "".join(command_output[:-1])
        base64_content = base64.b64encode(cert_text.encode()).decode()
        ca_file_path = f"{ssl_ca_dir}/{ca_file_name}"

        self.ssl_ca_certificate_object = SslCaCertificateObject(base64_content=base64_content, file_path=ca_file_path, file_name=ca_file_name, directory=ssl_ca_dir, cert_text=cert_text)

    def get_ssl_ca_certificate_object(self) -> SslCaCertificateObject:
        """
        Getter for SslCaCertificateObject.

        Returns:
            SslCaCertificateObject: The certificate object
        """
        return self.ssl_ca_certificate_object

    def get_base64_content(self) -> str:
        """
        Get base64-encoded certificate content.

        Returns:
            str: Base64-encoded certificate content
        """
        return self.ssl_ca_certificate_object.get_base64_content()

    def get_cert_text(self) -> str:
        """
        Get raw certificate text content.

        Returns:
            str: Raw certificate text
        """
        return self.ssl_ca_certificate_object.get_cert_text()
