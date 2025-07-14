class CephIOObject:
    """
    Object to hold the values of Ceph IO Object
    """

    def __init__(self):
        self.client: str = ""

    def get_client(self) -> str:
        """
        Getter for client

        Returns: client

        """
        return self.client
