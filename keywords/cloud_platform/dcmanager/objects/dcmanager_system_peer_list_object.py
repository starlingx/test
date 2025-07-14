class DcManagerSystemPeerListObject:
    """Represents a system peer from dcmanager system-peer list output.

    This class encapsulates the details of a system peer, including its ID, UUID, name,
    manager endpoint, and controller gateway address. It provides methods to get and set
    these attributes, as well as string representations for easy debugging and logging.
    It is typically used to parse the output of the 'dcmanager system-peer list' command
    and represent each peer as an object.

    Example output from 'dcmanager system-peer list':
    +----+--------------------------------------+-------------------------+---------------------------------------+----------------------------+
    | id | peer uuid                            | peer name               | manager endpoint                      | controller gateway address |
    +----+--------------------------------------+-------------------------+---------------------------------------+----------------------------+
    |  1 | 6f1a3a91-2efa-4976-beff-9fcb5fba1568 | SiteA-SiteB-system-peer | http://[2620:10a:a001:d41::1180]:5000 | fdff:719a:bf60:1103::1     |
    +----+--------------------------------------+-------------------------+---------------------------------------+----------------------------+

    """

    def __init__(self, id: str, peer_uuid: str, peer_name: str, manager_endpoint: str, controller_gateway_address: str):
        """Initialize the system peer object.

        Args:
            id (str): System peer ID.
            peer_uuid (str): UUID of the peer system.
            peer_name (str): Name of the peer system.
            manager_endpoint (str): Manager endpoint URL.
            controller_gateway_address (str): Controller gateway IP address.
        """
        self.id = id
        self.peer_uuid = peer_uuid
        self.peer_name = peer_name
        self.manager_endpoint = manager_endpoint
        self.controller_gateway_address = controller_gateway_address

    def get_id(self) -> str:
        """Get the system peer ID.

        Returns:
            str: System peer ID.
        """
        return self.id

    def set_id(self, id: str) -> None:
        """Set the system peer ID.

        Args:
            id (str): System peer ID.
        """
        self.id = id

    def get_peer_uuid(self) -> str:
        """Get the peer UUID.

        Returns:
            str: Peer UUID.
        """
        return self.peer_uuid

    def set_peer_uuid(self, peer_uuid: str) -> None:
        """Set the peer UUID.

        Args:
            peer_uuid (str): Peer UUID.
        """
        self.peer_uuid = peer_uuid

    def get_peer_name(self) -> str:
        """Get the peer name.

        Returns:
            str: Peer name.
        """
        return self.peer_name

    def set_peer_name(self, peer_name: str) -> None:
        """Set the peer name.

        Args:
            peer_name (str): Peer name.
        """
        self.peer_name = peer_name

    def get_manager_endpoint(self) -> str:
        """Get the manager endpoint.

        Returns:
            str: Manager endpoint URL.
        """
        return self.manager_endpoint

    def set_manager_endpoint(self, manager_endpoint: str) -> None:
        """Set the manager endpoint.

        Args:
            manager_endpoint (str): Manager endpoint URL.
        """
        self.manager_endpoint = manager_endpoint

    def get_controller_gateway_address(self) -> str:
        """Get the controller gateway address.

        Returns:
            str: Controller gateway IP address.
        """
        return self.controller_gateway_address

    def set_controller_gateway_address(self, controller_gateway_address: str) -> None:
        """Set the controller gateway address.

        Args:
            controller_gateway_address (str): Controller gateway IP address.
        """
        self.controller_gateway_address = controller_gateway_address

    def __str__(self) -> str:
        """String representation of the system peer object.

        Returns:
            str: String representation.
        """
        return f"{self.__class__.__name__}(Name={self.peer_name})"

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            str: String representation.
        """
        return self.__str__()
