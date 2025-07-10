class DcManagerSubcloudPeerGroupStatusObject:
    """Represents a subcloud peer group status from dcmanager subcloud-peer-group status output."""

    def __init__(self, peer_group_id: str, peer_group_name: str, total_subclouds: int, complete: int, waiting_for_migrate: int, rehoming: int, rehome_failed: int, managed: int, unmanaged: int):
        """Initialize the subcloud peer group status object.

        Args:
            peer_group_id (str): Peer group ID.
            peer_group_name (str): Name of the peer group.
            total_subclouds (int): Total number of subclouds.
            complete (int): Number of complete subclouds.
            waiting_for_migrate (int): Number of subclouds waiting for migration.
            rehoming (int): Number of subclouds in rehoming state.
            rehome_failed (int): Number of subclouds with failed rehoming.
            managed (int): Number of managed subclouds.
            unmanaged (int): Number of unmanaged subclouds.
        """
        self.peer_group_id = peer_group_id
        self.peer_group_name = peer_group_name
        self.total_subclouds = total_subclouds
        self.complete = complete
        self.waiting_for_migrate = waiting_for_migrate
        self.rehoming = rehoming
        self.rehome_failed = rehome_failed
        self.managed = managed
        self.unmanaged = unmanaged

    def get_peer_group_id(self) -> str:
        """Get the peer group ID.

        Returns:
            str: Peer group ID.
        """
        return self.peer_group_id

    def set_peer_group_id(self, peer_group_id: str) -> None:
        """Set the peer group ID.

        Args:
            peer_group_id (str): Peer group ID.
        """
        self.peer_group_id = peer_group_id

    def get_peer_group_name(self) -> str:
        """Get the peer group name.

        Returns:
            str: Peer group name.
        """
        return self.peer_group_name

    def set_peer_group_name(self, peer_group_name: str) -> None:
        """Set the peer group name.

        Args:
            peer_group_name (str): Peer group name.
        """
        self.peer_group_name = peer_group_name

    def get_total_subclouds(self) -> int:
        """Get the total number of subclouds.

        Returns:
            int: Total number of subclouds.
        """
        return self.total_subclouds

    def set_total_subclouds(self, total_subclouds: int) -> None:
        """Set the total number of subclouds.

        Args:
            total_subclouds (int): Total number of subclouds.
        """
        self.total_subclouds = total_subclouds

    def get_complete(self) -> int:
        """Get the number of complete subclouds.

        Returns:
            int: Number of complete subclouds.
        """
        return self.complete

    def set_complete(self, complete: int) -> None:
        """Set the number of complete subclouds.

        Args:
            complete (int): Number of complete subclouds.
        """
        self.complete = complete

    def get_waiting_for_migrate(self) -> int:
        """Get the number of subclouds waiting for migration.

        Returns:
            int: Number of subclouds waiting for migration.
        """
        return self.waiting_for_migrate

    def set_waiting_for_migrate(self, waiting_for_migrate: int) -> None:
        """Set the number of subclouds waiting for migration.

        Args:
            waiting_for_migrate (int): Number of subclouds waiting for migration.
        """
        self.waiting_for_migrate = waiting_for_migrate

    def get_rehoming(self) -> int:
        """Get the number of subclouds in rehoming state.

        Returns:
            int: Number of subclouds in rehoming state.
        """
        return self.rehoming

    def set_rehoming(self, rehoming: int) -> None:
        """Set the number of subclouds in rehoming state.

        Args:
            rehoming (int): Number of subclouds in rehoming state.
        """
        self.rehoming = rehoming

    def get_rehome_failed(self) -> int:
        """Get the number of subclouds with failed rehoming.

        Returns:
            int: Number of subclouds with failed rehoming.
        """
        return self.rehome_failed

    def set_rehome_failed(self, rehome_failed: int) -> None:
        """Set the number of subclouds with failed rehoming.

        Args:
            rehome_failed (int): Number of subclouds with failed rehoming.
        """
        self.rehome_failed = rehome_failed

    def get_managed(self) -> int:
        """Get the number of managed subclouds.

        Returns:
            int: Number of managed subclouds.
        """
        return self.managed

    def set_managed(self, managed: int) -> None:
        """Set the number of managed subclouds.

        Args:
            managed (int): Number of managed subclouds.
        """
        self.managed = managed

    def get_unmanaged(self) -> int:
        """Get the number of unmanaged subclouds.

        Returns:
            int: Number of unmanaged subclouds.
        """
        return self.unmanaged

    def set_unmanaged(self, unmanaged: int) -> None:
        """Set the number of unmanaged subclouds.

        Args:
            unmanaged (int): Number of unmanaged subclouds.
        """
        self.unmanaged = unmanaged

    def __str__(self) -> str:
        """String representation of the peer group status object."""
        return f"{self.__class__.__name__}(Name={self.peer_group_name})"

    def __repr__(self) -> str:
        """String representation for debugging."""
        return self.__str__()
