

class SystemHostAddrObject:

    """
    This class represents system host-addr as an object.
    """

    def __init__(self):
        self.uuid: str = None
        self.interface_uuid: str = None
        self.if_name: str = None
        self.forihostid: int = -1
        self.address: str = None
        self.prefix: int = -1
        self.enable_dad: bool = None
        self.pool_uuid:str = None


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

    def set_interface_uuid(self, interface_uuid):
        """
        Setter for host-addr interface_uuid
        """
        self.interface_uuid = interface_uuid

    def get_interface_uuid(self) -> str:
        """
        Getter for host-addr interface_uuid
        """
        return self.interface_uuid

    def set_forihostid(self, forihostid):
        """
        Setter for host interface forihostid
        """
        self.forihostid = forihostid

    def get_forihostid(self) -> int:
        """
        Getter for host interface forihostid
        """
        return self.forihostid

    def set_enable_dad(self, enable_dad):
        """
        Setter for host-addr enable_dad
        """
        self.enable_dad = enable_dad

    def get_enable_dad(self) -> bool:
        """
        Getter for host-addr enable_dad
        """
        return self.enable_dad

    def set_pool_uuid(self, pool_uuid):
        """
        Setter for host-addr pool_uuid
        """
        self.pool_uuid = pool_uuid

    def get_pool_uuid(self) -> str:
        """
        Getter for host-addr pool_uuid
        """
        return self.pool_uuid