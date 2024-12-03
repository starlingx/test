

class SystemHostAddrObject:

    """
    This class represents system host-addr as an object.
    """

    def __init__(self):
        self.uuid: str = None
        self.if_name: str = None
        self.address: str = None
        self.prefix: int = -1

    def set_uuid(self, uuid):
        """
        Setter for host-addr uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for host-addr UUID
        """
        return self.uuid

    def set_if_name(self, if_name):
        """
        Setter for this host if_name
        """
        self.if_name = if_name

    def get_if_name(self) -> str:
        """
        Getter for this host if_name
        """
        return self.if_name

    def set_address(self, address):
        """
        Setter for this host interface address
        """
        self.address = address

    def get_address(self) -> str:
        """
        Getter for this host interface address
        """
        return self.address

    def set_prefix(self, prefix):
        """
        Setter for host interface address prefix
        """
        self.prefix = prefix

    def get_prefix(self) -> int:
        """
        Getter for host interface address prefix
        """
        return self.prefix

