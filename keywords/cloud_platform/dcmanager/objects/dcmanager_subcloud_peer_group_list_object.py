class DcManagerSubcloudPeerGroupListObject:
    """Represents a subcloud peer group from dcmanager subcloud-peer-group list output."""

    def __init__(self, id: str, peer_group_name: str, group_priority: int, group_state: int, system_leader_id: str, system_leader_name: str, max_subcloud_rehoming: int):
        """Initialize the subcloud peer group object.

        Args:
            id (str): Peer group ID.
            peer_group_name (str): Name of the peer group.
            group_priority (int): Priority level of the peer group.
            group_state (int): State of the peer group.
            system_leader_id (str): ID of the system leader.
            system_leader_name (str): Name of the system leader.
            max_subcloud_rehoming (int): Maximum subcloud rehoming value.
        """
        self.id = id
        self.peer_group_name = peer_group_name
        self.group_priority = group_priority
        self.group_state = group_state
        self.system_leader_id = system_leader_id
        self.system_leader_name = system_leader_name
        self.max_subcloud_rehoming = max_subcloud_rehoming

    def get_id(self) -> str:
        """Get the peer group ID.

        Returns:
            str: Peer group ID.
        """
        return self.id

    def set_id(self, id: str) -> None:
        """Set the peer group ID.

        Args:
            id (str): Peer group ID.
        """
        self.id = id

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

    def get_group_priority(self) -> int:
        """Get the group priority.

        Returns:
            int: Group priority level.
        """
        return self.group_priority

    def set_group_priority(self, group_priority: int) -> None:
        """Set the group priority.

        Args:
            group_priority (int): Group priority level.
        """
        self.group_priority = group_priority

    def get_group_state(self) -> int:
        """Get the group state.

        Returns:
            int: Group state.
        """
        return self.group_state

    def set_group_state(self, group_state: int) -> None:
        """Set the group state.

        Args:
            group_state (int): Group state.
        """
        self.group_state = group_state

    def get_system_leader_id(self) -> str:
        """Get the system leader ID.

        Returns:
            str: System leader ID.
        """
        return self.system_leader_id

    def set_system_leader_id(self, system_leader_id: str) -> None:
        """Set the system leader ID.

        Args:
            system_leader_id (str): System leader ID.
        """
        self.system_leader_id = system_leader_id

    def get_system_leader_name(self) -> str:
        """Get the system leader name.

        Returns:
            str: System leader name.
        """
        return self.system_leader_name

    def set_system_leader_name(self, system_leader_name: str) -> None:
        """Set the system leader name.

        Args:
            system_leader_name (str): System leader name.
        """
        self.system_leader_name = system_leader_name

    def get_max_subcloud_rehoming(self) -> int:
        """Get the maximum subcloud rehoming value.

        Returns:
            int: Maximum subcloud rehoming value.
        """
        return self.max_subcloud_rehoming

    def set_max_subcloud_rehoming(self, max_subcloud_rehoming: int) -> None:
        """Set the maximum subcloud rehoming value.

        Args:
            max_subcloud_rehoming (int): Maximum subcloud rehoming value.
        """
        self.max_subcloud_rehoming = max_subcloud_rehoming

    def __str__(self) -> str:
        """String representation of the peer group object."""
        return f"{self.__class__.__name__}(Name={self.peer_group_name})"

    def __repr__(self) -> str:
        """String representation for debugging."""
        return self.__str__()
