"""Object class for ClusterObject."""


class ClusterObject:
    """Represents a ClusterObject resource."""

    def __init__(self):
        """Initialize ClusterObject."""
        self.uuid: str = None
        self.cluster_name: str = None
        self.type: str = None

    def set_uuid(self, uuid: str):
        """Set uuid.

        Args:
            uuid (str): The uuid.
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """Get uuid.

        Returns:
            str: The uuid.
        """
        return self.uuid

    def set_cluster_name(self, cluster_name: str):
        """Set cluster_name.

        Args:
            cluster_name (str): The cluster_name.
        """
        self.cluster_name = cluster_name

    def get_cluster_name(self) -> str:
        """Get cluster_name.

        Returns:
            str: The cluster_name.
        """
        return self.cluster_name

    def set_type(self, type: str):
        """Set type.

        Args:
            type (str): The type.
        """
        self.type = type

    def get_type(self) -> str:
        """Get type.

        Returns:
            str: The type.
        """
        return self.type

