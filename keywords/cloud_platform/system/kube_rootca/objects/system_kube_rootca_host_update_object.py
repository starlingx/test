class SystemKubeRootcaHostUpdateObject:
    """Object representing kube-rootca-host-update status."""

    def __init__(self):
        """Initialize host update object."""
        self.hostname = None
        self.personality = None
        self.state = None
        self.effective_rootca_cert = None
        self.target_rootca_cert = None

    def get_hostname(self) -> str:
        """Get hostname.

        Returns:
            str: Hostname value.
        """
        return self.hostname

    def set_hostname(self, hostname: str) -> None:
        """Set hostname.

        Args:
            hostname (str): Hostname value.
        """
        self.hostname = hostname

    def get_personality(self) -> str:
        """Get personality.

        Returns:
            str: Personality value.
        """
        return self.personality

    def set_personality(self, personality: str) -> None:
        """Set personality.

        Args:
            personality (str): Personality value.
        """
        self.personality = personality

    def get_state(self) -> str:
        """Get state.

        Returns:
            str: State value.
        """
        return self.state

    def set_state(self, state: str) -> None:
        """Set state.

        Args:
            state (str): State value.
        """
        self.state = state

    def get_effective_rootca_cert(self) -> str:
        """Get effective rootca cert.

        Returns:
            str: Effective certificate value.
        """
        return self.effective_rootca_cert

    def set_effective_rootca_cert(self, cert: str) -> None:
        """Set effective rootca cert.

        Args:
            cert (str): Effective certificate value.
        """
        self.effective_rootca_cert = cert

    def get_target_rootca_cert(self) -> str:
        """Get target rootca cert.

        Returns:
            str: Target certificate value.
        """
        return self.target_rootca_cert

    def set_target_rootca_cert(self, cert: str) -> None:
        """Set target rootca cert.

        Args:
            cert (str): Target certificate value.
        """
        self.target_rootca_cert = cert

    def is_updated_trust_both_cas(self) -> bool:
        """Check if host updated trust both cas.

        Returns:
            bool: True if updated, False otherwise.
        """
        return self.state == "updated-host-trust-both-cas"

    def is_updated_update_certs(self) -> bool:
        """Check if host updated certs.

        Returns:
            bool: True if updated, False otherwise.
        """
        return self.state == "updated-host-update-certs"

    def is_updated_trust_new_ca(self) -> bool:
        """Check if host updated trust new ca.

        Returns:
            bool: True if updated, False otherwise.
        """
        return self.state == "updated-host-trust-new-ca"
