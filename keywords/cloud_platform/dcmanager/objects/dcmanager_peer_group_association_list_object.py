class DcManagerPeerGroupAssociationListObject:
    """
    Represents a peer group association object in the DC Manager.

    Example output from 'dcmanager peer-group-association list' command:
    [sysadmin@controller-1 ~(keystone_admin)]$ dcmanager peer-group-association list
    +----+---------------+----------------+---------+-------------+---------------------+
    | id | peer_group_id | system_peer_id | type    | sync_status | peer_group_priority |
    +----+---------------+----------------+---------+-------------+---------------------+
    |  1 |             1 |              1 | primary |   in-sync   |                   1 |
    +----+---------------+----------------+---------+-------------+---------------------+

    """

    def __init__(self, id: str):
        self.id = id
        self.peer_group_id = -1
        self.system_peer_id = -1
        self.type = None
        self.sync_status = None
        self.peer_group_priority = -1

    def get_id(self) -> str:
        """Get the ID of the peer group association.

        Returns:
            str: ID of the peer group association.
        """
        return self.id

    def set_id(self, id: str) -> None:
        """Set the ID of the peer group association.

        Args:
            id (str): ID of the peer group association.
        """
        self.id = id

    def get_peer_group_id(self) -> int:
        """Get the peer group ID.

        Returns:
            int: Peer group ID.
        """
        return self.peer_group_id

    def set_peer_group_id(self, peer_group_id: int) -> None:
        """Set the peer group ID.

        Args:
            peer_group_id (int): Peer group ID.
        """
        self.peer_group_id = peer_group_id

    def get_system_peer_id(self) -> int:
        """Get the system peer ID.

        Returns:
            int: System peer ID.
        """
        return self.system_peer_id

    def set_system_peer_id(self, system_peer_id: int) -> None:
        """Set the system peer ID.

        Args:
            system_peer_id (int): System peer ID.
        """
        self.system_peer_id = system_peer_id

    def get_type(self) -> str:
        """Get the type.

        Returns:
            str: Type (primary or non-primary).
        """
        return self.type

    def set_type(self, type: str) -> None:
        """Set the Type

        Args:
            type (str): Type (primary or non-primary).
        """
        self.type = type

    def get_sync_status(self) -> str:
        """Get the synchronization status.

        Returns:
            str: Synchronization status.
        """
        return self.sync_status

    def set_sync_status(self, sync_status: str) -> None:
        """Set the synchronization status.

        Args:
            sync_status (str): Synchronization status.
        """
        self.sync_status = sync_status

    def get_peer_group_priority(self) -> int:
        """Get the peer group priority.

        Returns:
            int: Peer group priority.
        """
        return self.peer_group_priority

    def set_peer_group_priority(self, peer_group_priority: int) -> None:
        """Set the peer group priority.

        Args:
            peer_group_priority (int): Peer group priority.
        """
        self.peer_group_priority = peer_group_priority

    def __str__(self) -> str:
        """
        String representation of the peer group association object.

        Returns:
            str: String representation.
        """
        return f"{self.__class__.__name__}(ID={self.id})"

    def __repr__(self) -> str:
        """
        String representation for debugging.

        Returns:
            str: String representation.
        """
        return self.__str__()
