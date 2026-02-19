class SslCaCertificateObject:
    """
    Object class representing SSL CA certificate data.
    """

    def __init__(self, base64_content: str, file_path: str, file_name: str, directory: str, cert_text: str = None) -> None:
        """
        Constructor.

        Args:
            base64_content (str): Base64-encoded certificate content
            file_path (str): Full path to certificate file
            file_name (str): Certificate file name
            directory (str): Directory containing certificate
            cert_text (str, optional): Raw certificate text content
        """
        self.base64_content = base64_content
        self.file_path = file_path
        self.file_name = file_name
        self.directory = directory
        self.cert_text = cert_text

    def get_base64_content(self) -> str:
        """
        Get base64-encoded certificate content.

        Returns:
            str: Base64-encoded certificate content
        """
        return self.base64_content

    def get_file_path(self) -> str:
        """
        Get full path to certificate file.

        Returns:
            str: Full path to certificate file
        """
        return self.file_path

    def get_file_name(self) -> str:
        """
        Get certificate file name.

        Returns:
            str: Certificate file name
        """
        return self.file_name

    def get_directory(self) -> str:
        """
        Get directory containing certificate.

        Returns:
            str: Directory path
        """
        return self.directory

    def get_cert_text(self) -> str:
        """
        Get raw certificate text content.

        Returns:
            str: Raw certificate text
        """
        return self.cert_text
