class DcManagerSystemPeerShowObject:
    """Represents a system peer from dcmanager system-peer show output.

    [sysadmin@controller-1 ~(keystone_admin)]$ dcmanager system-peer show 1
    +-------------------------------+---------------------------------------+
    | Field                         | Value                                 |
    +-------------------------------+---------------------------------------+
    | id                            | 1                                     |
    | peer uuid                     | 6f1a3a91-2efa-4976-beff-9fcb5fba1568  |
    | peer name                     | SiteA-SiteB-system-peer               |
    | manager endpoint              | http://[2620:10a:a001:d41::1180]:5000 |
    | manager username              | admin                                 |
    | controller gateway address    | fdff:719a:bf60:1103::1                |
    | administrative state          | enabled                               |
    | heartbeat interval            | 60                                    |
    | heartbeat failure threshold   | 3                                     |
    | heartbeat failure policy      | alarm                                 |
    | heartbeat maintenance timeout | 600                                   |
    | availability state            | created                               |
    | created_at                    | 2025-07-07 11:47:06.532610            |
    | updated_at                    | None                                  |
    +-------------------------------+---------------------------------------+
    """

    def __init__(self, id: str, peer_uuid: str, peer_name: str, manager_endpoint: str, manager_username: str, controller_gateway_address: str, administrative_state: str, availability_state: str, heartbeat_interval: str, heartbeat_failure_threshold: str, heartbeat_failure_policy: str, heartbeat_maintenance_timeout: str):
        """Initialize the system peer show object.

        Args:
            id (str): System peer ID.
            peer_uuid (str): UUID of the peer system.
            peer_name (str): Name of the peer system.
            manager_endpoint (str): Manager endpoint URL.
            manager_username (str): Manager username.
            controller_gateway_address (str): Controller gateway IP address.
            administrative_state (str): Administrative state (enabled/disabled).
            availability_state (str): Availability state of the peer.
            heartbeat_interval (str): Heartbeat interval in seconds.
            heartbeat_failure_threshold (str): Heartbeat failure threshold.
            heartbeat_failure_policy (str): Policy for heartbeat failures.
            heartbeat_maintenance_timeout (str): Maintenance timeout in seconds.
        """
        self.id = id
        self.peer_uuid = peer_uuid
        self.peer_name = peer_name
        self.manager_endpoint = manager_endpoint
        self.manager_username = manager_username
        self.controller_gateway_address = controller_gateway_address
        self.administrative_state = administrative_state
        self.availability_state = availability_state
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_failure_threshold = heartbeat_failure_threshold
        self.heartbeat_failure_policy = heartbeat_failure_policy
        self.heartbeat_maintenance_timeout = heartbeat_maintenance_timeout

    def get_id(self) -> str:
        """Get the system peer ID."""
        return self.id

    def get_peer_uuid(self) -> str:
        """Get the peer UUID."""
        return self.peer_uuid

    def get_peer_name(self) -> str:
        """Get the peer name."""
        return self.peer_name

    def get_manager_endpoint(self) -> str:
        """Get the manager endpoint."""
        return self.manager_endpoint

    def get_manager_username(self) -> str:
        """Get the manager username."""
        return self.manager_username

    def get_controller_gateway_address(self) -> str:
        """Get the controller gateway address."""
        return self.controller_gateway_address

    def get_administrative_state(self) -> str:
        """Get the administrative state."""
        return self.administrative_state

    def get_heartbeat_interval(self) -> str:
        """Get the heartbeat interval."""
        return self.heartbeat_interval

    def get_heartbeat_failure_threshold(self) -> str:
        """Get the heartbeat failure threshold."""
        return self.heartbeat_failure_threshold

    def get_heartbeat_failure_policy(self) -> str:
        """Get the heartbeat failure policy."""
        return self.heartbeat_failure_policy

    def get_heartbeat_maintenance_timeout(self) -> str:
        """Get the heartbeat maintenance timeout."""
        return self.heartbeat_maintenance_timeout

    def get_availability_state(self) -> str:
        """Get the availability state."""
        return self.availability_state

    def get_created_at(self) -> str:
        """Get the creation timestamp."""
        return self.created_at

    def get_updated_at(self) -> str:
        """Get the last update timestamp."""
        return self.updated_at
