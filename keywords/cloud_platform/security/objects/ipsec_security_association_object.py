import re
from typing import Union


class IPSecSecurityAssociationObject:
    """Represents a single IPSec security association."""

    def __init__(self, name: str, association_data: str):
        """Initialize the security association object.

        Args:
            name (str): Name of the association.
            association_data (str): Raw association data from swanctl output.
        """
        self._name = name.strip() if name else ""
        self._association_data = association_data or ""
        self._local_cns = self._extract_cns("local")
        self._remote_cns = self._extract_cns("remote")
        self._remote_cns_set = set(self._remote_cns)

    def get_name(self) -> str:
        """Get the association name.

        Returns:
            str: Association name.
        """
        return self._name

    def get_association_data(self) -> str:
        """Get the raw association data.

        Returns:
            str: Raw association data.
        """
        return self._association_data

    def is_established(self) -> bool:
        """Check if the connection is established.

        Returns:
            bool: True if connection is established, False otherwise.
        """
        return re.search(r"\bESTABLISHED\b", self._association_data) is not None

    def get_local_cns(self) -> list[str]:
        """Get local Common Names.

        Returns:
            list[str]: List of local CNs.
        """
        return self._local_cns

    def get_remote_cns(self) -> list[str]:
        """Get remote Common Names.

        Returns:
            list[str]: List of remote CNs.
        """
        return self._remote_cns

    def has_local_cn_starting_with(self, prefix: str) -> bool:
        """Check if any local CN starts with the given prefix.

        Args:
            prefix (str): Prefix to check for.

        Returns:
            bool: True if any local CN starts with prefix, False otherwise.
        """
        if not prefix or not prefix.strip():
            return False
        return any(cn.startswith(prefix.strip()) for cn in self._local_cns)

    def has_remote_cn_in_set(self, cn_set: Union[set, list]) -> bool:
        """Check if any remote CN is in the given set.

        Args:
            cn_set (Union[set, list]): Set or list of CNs to check against.

        Returns:
            bool: True if any remote CN is in the set, False otherwise.
        """
        if not cn_set:
            return False
        return bool(self._remote_cns_set & (set(cn_set) if isinstance(cn_set, list) else cn_set))

    def _extract_cns(self, cn_type: str) -> list[str]:
        """Extract Common Names from association data.

        Args:
            cn_type (str): Type of CN to extract (local or remote).

        Returns:
            list[str]: List of CNs.
        """
        pattern = rf"{cn_type}\s+'CN=([^']*)'(?:\s|$)"
        return re.findall(pattern, self._association_data)
