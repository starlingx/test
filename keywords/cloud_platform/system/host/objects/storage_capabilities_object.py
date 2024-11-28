class StorageCapabilities:
    """
    Class for storage capabilities
    """

    def __init__(self):
        self.replication: int = -1
        self.min_replication: int = -1

    def set_replication(self, replication: int):
        """
        Setter for replication
        Args:
            replication:

        Returns:

        """
        self.replication = replication

    def get_replication(self) -> int:
        """
        Getter for replication
        Returns:

        """
        return self.replication

    def set_min_replication(self, min_replication: int):
        """
        Setter for min_replication
        Args:
            min_replication:

        Returns:

        """
        self.min_replication = min_replication

    def get_min_replication(self) -> int:
        """
        Getter for min_replication
        Returns:

        """
        return self.min_replication
