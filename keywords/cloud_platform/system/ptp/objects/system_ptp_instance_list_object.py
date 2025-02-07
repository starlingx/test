class SystemPTPInstanceListObject:
    """
    Represents a SystemPTPInstanceListObject with associated attributes.
    """

    def __init__(self):
        """
        Initializes a SystemPTPInstanceListObject instance.
        """
        self.uuid = None
        self.name = None
        self.service = None

    def set_uuid(self, uuid: str):
        """
        Setter for this ptp-instance-list uuid
        """
        self.uuid = uuid
    
    def get_uuid(self) -> str:
        """
        Getter for this ptp-instance-list uuid
        """
        return self.uuid

    def set_name(self, name: str):
        """
        Setter for this ptp-instance-list name
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for this ptp-instance-list name
        """
        return self.name
    
    def set_service(self, service: str):
        """
        Setter for this ptp-instance-list service
        """
        self.service = service

    def get_service(self) -> list[str]:
        """
        Getter for this ptp-instance-list service
        """
        return self.service


