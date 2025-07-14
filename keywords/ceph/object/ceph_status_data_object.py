class CephDataObject:
    """
    Object to hold the values of Ceph Data Object
    """

    def __init__(self):
        self.volumes: str = ""
        self.pools: str = ""
        self.objects: str = ""
        self.usage: str = ""
        self.pgs: str = ""

    def get_volumes(self) -> str:
        """
        Getter for volumes

        Returns: volumes

        """
        return self.volumes

    def get_pools(self) -> str:
        """
        Getter for pools

        Returns: pools

        """
        return self.pools

    def get_objects(self) -> str:
        """
        Getter for objects

        Returns: objects

        """
        return self.objects

    def get_usage(self) -> str:
        """
        Getter for usage

        Returns: usage

        """
        return self.usage

    def get_pgs(self) -> str:
        """
        Getter for pgs

        Returns: pgs

        """
        return self.pgs
