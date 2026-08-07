class CertificateInfoObject:
    """Represents parsed certificate information (subject, issuer, serial)."""

    def __init__(self, subject: str = "", issuer: str = "", serial: str = ""):
        """Initialize certificate info object.

        Args:
            subject (str): Certificate subject string.
            issuer (str): Certificate issuer string.
            serial (str): Certificate serial number (hex string).
        """
        self._subject = subject
        self._issuer = issuer
        self._serial = serial

    def get_subject(self) -> str:
        """Get certificate subject.

        Returns:
            str: Certificate subject string.
        """
        return self._subject

    def get_issuer(self) -> str:
        """Get certificate issuer.

        Returns:
            str: Certificate issuer string.
        """
        return self._issuer

    def get_serial(self) -> str:
        """Get certificate serial number.

        Returns:
            str: Certificate serial number in hex.
        """
        return self._serial

    def is_self_signed(self) -> bool:
        """Check if certificate is self-signed (subject equals issuer).

        Returns:
            bool: True if subject matches issuer.
        """
        return bool(self._subject and self._subject == self._issuer)
