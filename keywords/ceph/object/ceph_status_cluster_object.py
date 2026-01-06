class CephClusterObject:
    """
    Object to hold the values of Ceph Cluster Object
    """

    def __init__(self):
        self.id: str = ""
        self.health: str = ""

    def get_id(self) -> str:
        """
        Getter for id

        Returns: id

        """
        return self.id

    def get_health(self) -> str:
        """
        Getter for ceph health status

        Returns: health

        """
        return self.health
