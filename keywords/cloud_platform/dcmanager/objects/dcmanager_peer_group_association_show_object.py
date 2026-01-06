class DcManagerPeerGroupAssociationShowObject:
    """
    This class represents the show object for a peer group association in a data center manager.

    It is used to display the details of a specific peer group association.

    Example output from 'dcmanager peer-group-association show' command:
    [sysadmin@controller-0 ~(keystone_admin)]$ dcmanager peer-group-association show 1
        +---------------------+----------------------------+
        | Field               | Value                      |
        +---------------------+----------------------------+
        | id                  | 1                          |
        | peer_group_id       | 1                          |
        | system_peer_id      | 1                          |
        | association_type    | primary                    |
        | sync_status         | syncing                    |
        | peer_group_priority | 1                          |
        | sync_message        | None                       |
        | created_at          | 2025-07-10 07:41:11.666381 |
        | updated_at          | 2025-07-14 17:58:29.211914 |
        +---------------------+----------------------------+
    """

    def __init__(self, id: int):
        """
        Initializes the show object with the given peer group association.

        Args:
            id (int): The ID of the peer group association.
        """
        self.id: int = id
        self.peer_group_id: int = -1
        self.system_peer_id: int = -1
        self.association_type: str = None
        self.sync_status: str = None
        self.peer_group_priority: int = -1
        self.sync_message: str = None
        self.created_at: str = None
        self.updated_at: str = None

    def get_id(self) -> int:
        """
        Getter for the ID of the peer group association.

        Returns:
            int: The ID of the peer group association.
        """
        return self.id

    def set_id(self, id: int) -> None:
        """
        Setter for the ID of the peer group association.

        Args:
            id (int): The ID of the peer group association.
        """
        self.id = id

    def get_peer_group_id(self) -> int:
        """
        Getter for the peer group ID.

        Returns:
            int: The ID of the peer group.
        """
        return self.peer_group_id

    def set_peer_group_id(self, peer_group_id: int) -> None:
        """
        Setter for the peer group ID.

        Args:
            peer_group_id (int): The ID of the peer group.
        """
        self.peer_group_id = peer_group_id

    def get_system_peer_id(self) -> int:
        """
        Getter for the system peer ID.

        Returns:
            int: The ID of the system peer.
        """
        return self.system_peer_id

    def set_system_peer_id(self, system_peer_id: int) -> None:
        """
        Setter for the system peer ID.

        Args:
            system_peer_id (int): The ID of the system peer.
        """
        self.system_peer_id = system_peer_id

    def get_association_type(self) -> str:
        """
        Getter for the association type.

        Returns:
            str: The type of association.
        """
        return self.association_type

    def set_association_type(self, association_type: str) -> None:
        """
        Setter for the association type.

        Args:
            association_type (str): The type of association.
        """
        self.association_type = association_type

    def get_sync_status(self) -> str:
        """
        Getter for the sync status.

        Returns:
            str: The sync status of the peer group association.
        """
        return self.sync_status

    def set_sync_status(self, sync_status: str) -> None:
        """
        Setter for the sync status.

        Args:
            sync_status (str): The sync status of the peer group association.
        """
        self.sync_status = sync_status

    def get_peer_group_priority(self) -> int:
        """
        Getter for the peer group priority.

        Returns:
            int: The priority of the peer group.
        """
        return self.peer_group_priority

    def set_peer_group_priority(self, peer_group_priority: int) -> None:
        """
        Setter for the peer group priority.

        Args:
            peer_group_priority (int): The priority of the peer group.
        """
        self.peer_group_priority = peer_group_priority

    def get_sync_message(self) -> str:
        """
        Getter for the sync message.

        Returns:
            str: The message related to the sync status.
        """
        return self.sync_message

    def set_sync_message(self, sync_message: str) -> None:
        """
        Setter for the sync message.

        Args:
            sync_message (str): The message related to the sync status.
        """
        self.sync_message = sync_message

    def get_created_at(self) -> str:
        """
        Getter for the creation timestamp.

        Returns:
            str: The timestamp when the peer group association was created.
        """
        return self.created_at

    def set_created_at(self, created_at: str) -> None:
        """
        Setter for the creation timestamp.

        Args:
            created_at (str): The timestamp when the peer group association was created.
        """
        self.created_at = created_at

    def get_updated_at(self) -> str:
        """
        Getter for the update timestamp.

        Returns:
            str: The timestamp when the peer group association was last updated.
        """
        return self.updated_at

    def set_updated_at(self, updated_at: str) -> None:
        """
        Setter for the update timestamp.

        Args:
            updated_at (str): The timestamp when the peer group association was last updated.
        """
        self.updated_at = updated_at

    def __str__(self) -> str:
        """
        String representation of the peer group association show object.

        Returns:
            str: String representation.
        """
        return f"{self.__class__.__name__}(ID={self.id}, Status={self.sync_status})"

    def __repr__(self) -> str:
        """Official string representation of the peer group association object.

        Returns:
            str: Official string representation of the object.
        """
        return self.__str__()
