class SystemKubeRootcaUpdateObject:
    """Object representing kube-rootca-update status."""

    def __init__(self):
        """Initialize kube rootca update object."""
        self.uuid = None
        self.state = None
        self.from_rootca_cert = None
        self.to_rootca_cert = None
        self.created_at = None
        self.updated_at = None

    def get_uuid(self) -> str:
        """Get UUID.

        Returns:
            str: UUID value.
        """
        return self.uuid

    def set_uuid(self, uuid: str) -> None:
        """Set UUID.

        Args:
            uuid (str): UUID value.
        """
        self.uuid = uuid

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

    def get_from_rootca_cert(self) -> str:
        """Get from rootca cert.

        Returns:
            str: From certificate value.
        """
        return self.from_rootca_cert

    def set_from_rootca_cert(self, cert: str) -> None:
        """Set from rootca cert.

        Args:
            cert (str): From certificate value.
        """
        self.from_rootca_cert = cert

    def get_to_rootca_cert(self) -> str:
        """Get to rootca cert.

        Returns:
            str: To certificate value.
        """
        return self.to_rootca_cert

    def set_to_rootca_cert(self, cert: str) -> None:
        """Set to rootca cert.

        Args:
            cert (str): To certificate value.
        """
        self.to_rootca_cert = cert

    def get_created_at(self) -> str:
        """Get created at timestamp.

        Returns:
            str: Created timestamp.
        """
        return self.created_at

    def set_created_at(self, created_at: str) -> None:
        """Set created at timestamp.

        Args:
            created_at (str): Created timestamp.
        """
        self.created_at = created_at

    def get_updated_at(self) -> str:
        """Get updated at timestamp.

        Returns:
            str: Updated timestamp.
        """
        return self.updated_at

    def set_updated_at(self, updated_at: str) -> None:
        """Set updated at timestamp.

        Args:
            updated_at (str): Updated timestamp.
        """
        self.updated_at = updated_at

    def is_update_started(self) -> bool:
        """Check if update is started.

        Returns:
            bool: True if update started, False otherwise.
        """
        return self.state == "update-started"

    def is_update_completed(self) -> bool:
        """Check if update is completed.

        Returns:
            bool: True if update completed, False otherwise.
        """
        return self.state == "update-completed"

    def is_cert_generated(self) -> bool:
        """Check if new cert is generated.

        Returns:
            bool: True if cert generated, False otherwise.
        """
        return self.state == "update-new-rootca-cert-generated"
