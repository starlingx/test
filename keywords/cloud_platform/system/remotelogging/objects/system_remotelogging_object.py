class SystemRemoteloggingObject:
    """
    This class represents a service as an object.
    This is typically a line in the system remotelogging output table.
    """

    def __init__(self):
        self.uuid:str = None
        self.ip_address:str = None
        self.enabled:bool = None
        self.transport:str = None
        self.port: int = -1
        self.created_at: str = None
        self.updated_at: str = None


    def set_uuid(self, uuid: str):
        """
        Setter for the uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for the uuid
        """
        return self.uuid

    def set_ip_address(self, ip_address: str):
        """
        Setter for the ip_address
        """
        self.ip_address = ip_address

    def get_ip_address(self) -> str:
        """
        Getter for ip_address
        """
        return self.ip_address

    def set_enabled(self, enabled: bool):
        """
        Setter for the enabled
        """
        self.enabled = enabled

    def get_enabled(self) -> bool:
        """
        Getter for the enabled
        """
        return self.enabled

    def set_transport(self, transport: str):
        """
        Setter for the transport
        """
        self.transport = transport

    def get_transport(self) -> str:
        """
        Getter for the transport
        """
        return self.transport

    def set_port(self, port: int):
        """
        Setter for the port
        """
        self.port = port

    def get_port(self) -> int:
        """
        Getter for the port
        """
        return self.port

    def set_created_at(self, created_at: str):
        """
        Setter for created_at
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """
        Getter for created_at
        """
        return self.created_at

    def set_updated_at(self, updated_at: str):
        """
        Setter for updated_at
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """
        Getter for updated_at
        """
        return self.updated_at
