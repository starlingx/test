"""System certificate show object."""


class SystemCertificateShowObject:
    """Represents parsed output from system certificate-show command."""

    def __init__(self):
        """Initialize with default values."""
        self.residual_time = None
        self.version = None
        self.serial_number = None
        self.issuer = None
        self.not_before = None
        self.not_after = None
        self.subject = None
        self.key_size = None
        self.signature_algorithm = None
        self.file_path = None
        self.renewal = None
        self.namespace = None
        self.secret = None

    def set_residual_time(self, residual_time: str) -> None:
        """Set residual time.

        Args:
            residual_time (str): Residual time (e.g., "87d").
        """
        self.residual_time = residual_time

    def get_residual_time(self) -> str:
        """Get residual time.

        Returns:
            str: Residual time (e.g., "87d").
        """
        return self.residual_time

    def set_version(self, version: str) -> None:
        """Set version.

        Args:
            version (str): Certificate version (e.g., "v3").
        """
        self.version = version

    def get_version(self) -> str:
        """Get version.

        Returns:
            str: Certificate version (e.g., "v3").
        """
        return self.version

    def set_serial_number(self, serial_number: str) -> None:
        """Set serial number.

        Args:
            serial_number (str): Serial number hex string.
        """
        self.serial_number = serial_number

    def get_serial_number(self) -> str:
        """Get serial number.

        Returns:
            str: Serial number hex string.
        """
        return self.serial_number

    def set_issuer(self, issuer: str) -> None:
        """Set issuer.

        Args:
            issuer (str): Issuer DN string.
        """
        self.issuer = issuer

    def get_issuer(self) -> str:
        """Get issuer.

        Returns:
            str: Issuer DN string.
        """
        return self.issuer

    def set_not_before(self, not_before: str) -> None:
        """Set not before.

        Args:
            not_before (str): Not-before date string.
        """
        self.not_before = not_before

    def get_not_before(self) -> str:
        """Get not before.

        Returns:
            str: Not-before date string.
        """
        return self.not_before

    def set_not_after(self, not_after: str) -> None:
        """Set not after.

        Args:
            not_after (str): Not-after date string.
        """
        self.not_after = not_after

    def get_not_after(self) -> str:
        """Get not after.

        Returns:
            str: Not-after date string.
        """
        return self.not_after

    def set_subject(self, subject: str) -> None:
        """Set subject.

        Args:
            subject (str): Subject DN string.
        """
        self.subject = subject

    def get_subject(self) -> str:
        """Get subject.

        Returns:
            str: Subject DN string.
        """
        return self.subject

    def set_key_size(self, key_size: str) -> None:
        """Set key size.

        Args:
            key_size (str): Key size (e.g., "(384 bit)").
        """
        self.key_size = key_size

    def get_key_size(self) -> str:
        """Get key size.

        Returns:
            str: Key size (e.g., "(384 bit)").
        """
        return self.key_size

    def set_signature_algorithm(self, signature_algorithm: str) -> None:
        """Set signature algorithm.

        Args:
            signature_algorithm (str): Signature algorithm (e.g., "ecdsa-with-SHA384").
        """
        self.signature_algorithm = signature_algorithm

    def get_signature_algorithm(self) -> str:
        """Get signature algorithm.

        Returns:
            str: Signature algorithm (e.g., "ecdsa-with-SHA384").
        """
        return self.signature_algorithm

    def set_file_path(self, file_path: str) -> None:
        """Set file path.

        Args:
            file_path (str): Certificate file path on the system.
        """
        self.file_path = file_path

    def get_file_path(self) -> str:
        """Get file path.

        Returns:
            str: Certificate file path on the system.
        """
        return self.file_path

    def set_renewal(self, renewal: str) -> None:
        """Set renewal.

        Args:
            renewal (str): Renewal status (e.g., "Automatic").
        """
        self.renewal = renewal

    def get_renewal(self) -> str:
        """Get renewal.

        Returns:
            str: Renewal status (e.g., "Automatic").
        """
        return self.renewal

    def set_namespace(self, namespace: str) -> None:
        """Set namespace.

        Args:
            namespace (str): Kubernetes namespace.
        """
        self.namespace = namespace

    def get_namespace(self) -> str:
        """Get namespace.

        Returns:
            str: Kubernetes namespace.
        """
        return self.namespace

    def set_secret(self, secret: str) -> None:
        """Set secret.

        Args:
            secret (str): Kubernetes secret name.
        """
        self.secret = secret

    def get_secret(self) -> str:
        """Get secret.

        Returns:
            str: Kubernetes secret name.
        """
        return self.secret

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable certificate show info.
        """
        return f"CertShow({self.secret}, subject={self.subject}, renewal={self.renewal}, key_size={self.key_size})"
