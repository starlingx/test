class SystemPTPInstanceObject:
    """
    Represents a SystemPTPInstanceObject with associated attributes.
    """

    def __init__(self):
        """
        Initializes a SystemPTPInstanceObject instance.
        """
        self.uuid = None
        self.name = None
        self.service = None
        self.hostnames = []
        self.parameters = []


    def set_uuid(self, uuid: str):
        """
        Setter for this ptp-instance uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for this ptp-instance uuid
        """
        return self.uuid

    def set_name(self, name: str):
        """
        Setter for this ptp-instance name
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for this ptp-instance name
        """
        return self.name

    def set_service(self, service: str):
        """
        Setter for this ptp-instance service
        """
        self.service = service

    def get_service(self) -> str:
        """
        Getter for this ptp-instance service
        """
        return self.service

    def set_hostnames(self, hostnames: list):
        """
        Setter for this ptp-instance hostnames
        """
        self.hostnames = hostnames

    def get_hostnames(self) -> list:
        """
        Getter for this ptp-instance hostnames
        """
        return self.hostnames

    def set_parameters(self, parameters: list):
        """
        Setter for this ptp-instance parameters
        """
        self.parameters = parameters

    def get_parameters(self) -> list[str]:
        """
        Getter for this ptp-instance parameters
        """
        return self.parameters
    
    