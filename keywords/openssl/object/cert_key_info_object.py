"""Certificate key information object."""


class CertKeyInfoObject:
    """Represents key algorithm information extracted from an X.509 certificate."""

    def __init__(self):
        """Initialize CertKeyInfoObject with default values."""
        self.type = None
        self.curve = None
        self.size = None

    def set_type(self, key_type: str) -> None:
        """Set the key type.

        Args:
            key_type (str): Key type - "ECDSA" or "RSA".
        """
        self.type = key_type

    def get_type(self) -> str:
        """Get the key type.

        Returns:
            str: Key type - "ECDSA" or "RSA".
        """
        return self.type

    def set_curve(self, curve: str) -> None:
        """Set the ECDSA curve name.

        Args:
            curve (str): Curve name (e.g., "secp384r1", "secp521r1", "prime256v1").
        """
        self.curve = curve

    def get_curve(self) -> str:
        """Get the ECDSA curve name.

        Returns:
            str: Curve name or None for RSA.
        """
        return self.curve

    def set_size(self, size: int) -> None:
        """Set the key size in bits.

        Args:
            size (int): Key size (e.g., 384, 521, 256, 3072, 4096).
        """
        self.size = size

    def get_size(self) -> int:
        """Get the key size in bits.

        Returns:
            int: Key size in bits.
        """
        return self.size

    def is_ecdsa(self) -> bool:
        """Check if the key type is ECDSA.

        Returns:
            bool: True if ECDSA.
        """
        return self.type == "ECDSA"

    def is_rsa(self) -> bool:
        """Check if the key type is RSA.

        Returns:
            bool: True if RSA.
        """
        return self.type == "RSA"

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable key info.
        """
        if self.is_ecdsa():
            return f"ECDSA {self.curve} ({self.size} bit)"
        elif self.is_rsa():
            return f"RSA ({self.size} bit)"
        return f"Unknown (type={self.type}, size={self.size})"
