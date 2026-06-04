"""Keypair list output parsing and manipulation."""

from typing import Dict, List

from keywords.openstack.resources.keypairs.object.keypair_object import KeypairObject


class KeypairListOutput:
    """Parses and provides access to a collection of KeypairObjects."""

    def __init__(self, raw_keypairs: List[Dict]) -> None:
        """Initialize KeypairListOutput from raw keypair dicts.

        Args:
            raw_keypairs (List[Dict]): List of keypair dictionaries from OpenStack SDK.
        """
        self._keypairs = []
        for raw in raw_keypairs:
            keypair = KeypairObject()
            keypair.set_name(raw.get("name", ""))
            keypair.set_id(raw.get("id", ""))
            keypair.set_fingerprint(raw.get("fingerprint", ""))
            keypair.set_public_key(raw.get("public_key", ""))
            keypair.set_private_key(raw.get("private_key"))
            keypair.set_type(raw.get("type", ""))
            self._keypairs.append(keypair)

    def get_keypairs(self) -> List[KeypairObject]:
        """Get all keypair objects.

        Returns:
            List[KeypairObject]: List of keypair objects.
        """
        return self._keypairs

    def get_keypair_by_name(self, name: str) -> KeypairObject:
        """Get a keypair by name.

        Args:
            name (str): Keypair name.

        Returns:
            KeypairObject: Matching keypair.

        Raises:
            ValueError: If no keypair with the given name is found.
        """
        for keypair in self._keypairs:
            if keypair.get_name() == name:
                return keypair
        raise ValueError(f"Keypair '{name}' not found")

    def is_keypair_present(self, name: str) -> bool:
        """Check if a keypair with the given name exists.

        Args:
            name (str): Keypair name.

        Returns:
            bool: True if found.
        """
        for keypair in self._keypairs:
            if keypair.get_name() == name:
                return True
        return False

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return f"KeypairListOutput(count={len(self._keypairs)})"
