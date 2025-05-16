class CephServicesObject:
    """
    Object to hold the values of Ceph Services Object
    """

    def __init__(self):
        self.mon: str = ""
        self.mgr: str = ""
        self.mds: str = ""
        self.osd: str = ""

    def get_mon(self) -> str:
        """
        Getter for mon

        Returns: mon

        """
        return self.mon

    def get_mgr(self) -> str:
        """
        Getter for mgr

        Returns: mgr

        """
        return self.mgr

    def get_mds(self) -> str:
        """
        Getter for mds

        Returns: mds

        """
        return self.mds

    def get_osd(self) -> str:
        """
        Getter for osd

        Returns: osd

        """
        return self.osd
