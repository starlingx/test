class IPSecCertificateObject:
    """Object representing an IPSec certificate with subject/issuer information and MD5 hash."""

    def __init__(self, cert_type: str, hostname: str, cert_path: str, subject: str = "", issuer: str = "", md5_hash: str = ""):
        """Initialize certificate object.

        Args:
            cert_type (str): Type of certificate (key, cert, ica, root, k8s_cert).
            hostname (str): Hostname where certificate is located.
            cert_path (str): Path to certificate file.
            subject (str): Certificate subject information.
            issuer (str): Certificate issuer information.
            md5_hash (str): MD5 hash of the certificate.
        """
        self._cert_type = cert_type
        self._hostname = hostname
        self._cert_path = cert_path
        self._subject = subject
        self._issuer = issuer
        self._md5_hash = md5_hash

    def get_cert_type(self) -> str:
        """Get certificate type.

        Returns:
            str: Certificate type.
        """
        return self._cert_type

    def get_hostname(self) -> str:
        """Get hostname.

        Returns:
            str: Hostname where certificate is located.
        """
        return self._hostname

    def get_cert_path(self) -> str:
        """Get certificate path.

        Returns:
            str: Path to certificate file.
        """
        return self._cert_path

    def get_subject(self) -> str:
        """Get certificate subject.

        Returns:
            str: Certificate subject information.
        """
        return self._subject

    def get_issuer(self) -> str:
        """Get certificate issuer.

        Returns:
            str: Certificate issuer information.
        """
        return self._issuer

    def get_md5_hash(self) -> str:
        """Get MD5 hash.

        Returns:
            str: MD5 hash of the certificate.
        """
        return self._md5_hash

    def has_valid_subject(self) -> bool:
        """Check if subject is valid.

        Returns:
            bool: True if subject is not empty.
        """
        return bool(self._subject and self._subject.strip())

    def has_valid_issuer(self) -> bool:
        """Check if issuer is valid.

        Returns:
            bool: True if issuer is not empty.
        """
        return bool(self._issuer and self._issuer.strip())

    def has_valid_md5(self) -> bool:
        """Check if MD5 hash is valid.

        Returns:
            bool: True if MD5 hash is not empty.
        """
        return bool(self._md5_hash and self._md5_hash.strip())

    def matches_md5(self, other_md5: str) -> bool:
        """Check if MD5 matches another hash.

        Args:
            other_md5 (str): Other MD5 hash to compare.

        Returns:
            bool: True if MD5 hashes match.
        """
        return self._md5_hash == other_md5

    def matches_issuer(self, other_issuer: str) -> bool:
        """Check if issuer matches another issuer.

        Args:
            other_issuer (str): Other issuer to compare.

        Returns:
            bool: True if issuers match.
        """
        return self._compare_dn(self._issuer, other_issuer)

    def _compare_dn(self, dn1: str, dn2: str) -> bool:
        """Compare two DN strings after normalization.

        Args:
            dn1 (str): First DN string.
            dn2 (str): Second DN string.

        Returns:
            bool: True if DNs match after normalization.
        """
        if not dn1 or not dn2:
            return False
        return self._normalize_dn(dn1) == self._normalize_dn(dn2)

    def _normalize_dn(self, dn_string: str) -> str:
        """Normalize DN string for comparison.

        Args:
            dn_string (str): DN string to normalize.

        Returns:
            str: Normalized DN string.
        """
        if not dn_string:
            return ""

        # Normalize spacing and parse components
        normalized = dn_string.replace(" + ", "+").replace(" = ", "=")
        components = {}

        for part in normalized.split(","):
            if "=" in part.strip():
                key, value = part.strip().split("=", 1)
                key, value = key.strip(), value.strip()
                if key and value:
                    components[key] = f"{components.get(key, '')}{'+' if key in components else ''}{value}"

        # Return ordered components
        order = ["CN", "OU", "O", "L", "ST", "C"]
        return ",".join(f"{k}={components[k]}" for k in order if k in components)

    def is_self_signed(self) -> bool:
        """Check if certificate is self-signed.

        Returns:
            bool: True if subject equals issuer.
        """
        return self._compare_dn(self._subject, self._issuer)
