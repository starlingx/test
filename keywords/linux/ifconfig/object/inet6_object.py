class Inet6:
    """
    This class represents an Inet6 (IPv6) attributes as an object.
    """

    def __init__(self):
        """
        Constructor

        Args: None.

        """
        self.inet6: str = None
        self.prefix_len: int = -1
        self.scope_id: str = None

    def set_inet6(self, inet6: str) -> None:
        """
        Sets the inet6 (IPv6 address).
        """
        self.inet6 = inet6

    def get_inet6(self) -> str:
        """
        Gets the inet6 (IPv6 address).
        """
        return self.inet6

    def set_prefix_len(self, prefix_len: int) -> None:
        """
        Sets the prefix length.
        """
        self.prefix_len = prefix_len

    def get_prefix_len(self) -> int:
        """
        Gets the prefix length.
        """
        return self.prefix_len

    def set_scope_id(self, scope_id: str) -> None:
        """
        Sets the scope ID.
        """
        self.scope_id = scope_id

    def get_scope_id(self) -> str:
        """
        Gets the scope ID.
        """
        return self.scope_id

    def is_global(self) -> bool:
        """
        Returns True if this Inet6 has a global IPv6 address, False otherwise.
        """
        return self.get_scope_id() == "0x0<global>"
