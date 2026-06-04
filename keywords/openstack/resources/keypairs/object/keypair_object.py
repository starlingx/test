"""Keypair object representation."""

from typing import Optional


class KeypairObject:
    """Represents a single OpenStack keypair."""

    def __init__(self) -> None:
        """Initialize an empty KeypairObject."""
        self._name = ""
        self._id = ""
        self._fingerprint = ""
        self._public_key = ""
        self._private_key: Optional[str] = None
        self._type = ""

    def get_name(self) -> str:
        """Get the keypair name.

        Returns:
            str: Keypair name.
        """
        return self._name

    def set_name(self, name: str) -> None:
        """Set the keypair name.

        Args:
            name (str): Keypair name.
        """
        self._name = name

    def get_id(self) -> str:
        """Get the keypair ID.

        Returns:
            str: Keypair ID.
        """
        return self._id

    def set_id(self, keypair_id: str) -> None:
        """Set the keypair ID.

        Args:
            keypair_id (str): Keypair ID.
        """
        self._id = keypair_id

    def get_fingerprint(self) -> str:
        """Get the keypair fingerprint.

        Returns:
            str: Keypair fingerprint.
        """
        return self._fingerprint

    def set_fingerprint(self, fingerprint: str) -> None:
        """Set the keypair fingerprint.

        Args:
            fingerprint (str): Keypair fingerprint.
        """
        self._fingerprint = fingerprint

    def get_public_key(self) -> str:
        """Get the public key.

        Returns:
            str: Public key string.
        """
        return self._public_key

    def set_public_key(self, public_key: str) -> None:
        """Set the public key.

        Args:
            public_key (str): Public key string.
        """
        self._public_key = public_key

    def get_private_key(self) -> Optional[str]:
        """Get the private key (only available at creation time).

        Returns:
            Optional[str]: Private key string, or None.
        """
        return self._private_key

    def set_private_key(self, private_key: Optional[str]) -> None:
        """Set the private key.

        Args:
            private_key (Optional[str]): Private key string.
        """
        self._private_key = private_key

    def get_type(self) -> str:
        """Get the keypair type.

        Returns:
            str: Keypair type (e.g. 'ssh').
        """
        return self._type

    def set_type(self, keypair_type: str) -> None:
        """Set the keypair type.

        Args:
            keypair_type (str): Keypair type.
        """
        self._type = keypair_type

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return f"KeypairObject(name={self._name}, fingerprint={self._fingerprint})"
