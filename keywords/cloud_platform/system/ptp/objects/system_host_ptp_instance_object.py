class SystemHostPTPInstanceObject:
    """
    Represents a SystemHostPTPInstanceObject with associated attributes.
    """

    def __init__(self):
        """
        Initializes a SystemHostPTPInstanceObject instance.
        """
        self.uuid = None
        self.name = None
        self.service = None

    def set_uuid(self, uuid: str):
        """
        Setter for this host-ptp-instance uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for this host-ptp-instance uuid
        """
        return self.uuid

    def set_name(self, name: str):
        """
        Setter for this host-ptp-instance name
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for this host-ptp-instance name
        """
        return self.name

    def set_service(self, service: str):
        """
        Setter for this host-ptp-instance service
        """
        self.service = service

    def get_service(self) -> str:
        """
        Getter for this host-ptp-instance service
        """
        return self.service
    
    