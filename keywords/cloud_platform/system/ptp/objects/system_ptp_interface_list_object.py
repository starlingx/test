class SystemPTPInterfaceListObject:
    """
    Represents a SystemPTPInterfaceListObject with associated attributes.
    """

    def __init__(self):
        """
        Initializes a SystemPTPInterfaceListObject instance.
        """
        self.uuid = None
        self.name = None
        self.ptp_instance_name = None
        self.parameters = []


    def set_uuid(self, uuid: str):
        """
        Setter for this ptp-interface-list uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for this ptp-interface-list uuid
        """
        return self.uuid

    def set_name(self, name: str):
        """
        Setter for this ptp-interface-list name
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for this ptp-interface-list name
        """
        return self.name

    def set_ptp_instance_name(self, ptp_instance_name: str):
        """
        Setter for this ptp-interface-list ptp_instance_name
        """
        self.ptp_instance_name = ptp_instance_name

    def get_ptp_instance_name(self) -> str:
        """
        Getter for this ptp-interface-list ptp_instance_name
        """
        return self.ptp_instance_name

    def set_parameters(self, parameters: list):
        """
        Setter for this ptp-interface-list parameters
        """
        self.parameters = parameters

    def get_parameters(self) -> list[str]:
        """
        Getter for this ptp-interface-list parameters
        """
        return self.parameters
    
    