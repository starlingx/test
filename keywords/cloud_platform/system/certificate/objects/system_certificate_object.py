"""System Certificate Object."""


class SystemCertificateObject:
    """Object representing a system certificate."""

    def __init__(self, name: str = None):
        """Initialize system certificate object.

        Args:
            name (str): Certificate name.
        """
        self.name = name
        self.residual_time = None
        self.issue_date = None
        self.expiry_date = None
        self.issuer = None
        self.subject = None
        self.renewal = None
        self.file_path = None

    def set_name(self, name: str) -> None:
        """Set certificate name.

        Args:
            name (str): Certificate name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get certificate name.

        Returns:
            str: Certificate name.
        """
        return self.name

    def set_issuer(self, issuer: str) -> None:
        """Set certificate issuer.

        Args:
            issuer (str): Certificate issuer.
        """
        self.issuer = issuer

    def get_issuer(self) -> str:
        """Get certificate issuer.

        Returns:
            str: Certificate issuer.
        """
        return self.issuer

    def set_subject(self, subject: str) -> None:
        """Set certificate subject.

        Args:
            subject (str): Certificate subject.
        """
        self.subject = subject

    def get_subject(self) -> str:
        """Get certificate subject.

        Returns:
            str: Certificate subject.
        """
        return self.subject

    def set_renewal(self, renewal: str) -> None:
        """Set renewal type.

        Args:
            renewal (str): Renewal type.
        """
        self.renewal = renewal

    def get_renewal(self) -> str:
        """Get renewal type.

        Returns:
            str: Renewal type.
        """
        return self.renewal

    def is_self_signed(self) -> bool:
        """Check if certificate is self-signed.

        Returns:
            bool: True if issuer equals subject, False otherwise.
        """
        return self.issuer == self.subject if self.issuer and self.subject else False

    def set_file_path(self, file_path: str) -> None:
        """Set certificate file path.

        Args:
            file_path (str): Certificate file path.
        """
        self.file_path = file_path

    def get_file_path(self) -> str:
        """Get certificate file path.

        Returns:
            str: Certificate file path.
        """
        return self.file_path
