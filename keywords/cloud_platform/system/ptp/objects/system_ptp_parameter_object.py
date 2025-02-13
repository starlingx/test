class SystemPTPParameterObject:
    """
    Represents a SystemPTPParameterObject with associated attributes.
    """

    def __init__(self):
        """
        Initializes a SystemPTPParameterObject instance.
        """
        self.uuid = None
        self.name = None
        self.value = None


    def set_uuid(self, uuid: str):
        """
        Setter for this ptp-parameter uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for this ptp-parameter uuid
        """
        return self.uuid

    def set_name(self, name: str):
        """
        Setter for this ptp-parameter name
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for this ptp-parameter name
        """
        return self.name

    def set_value(self, value: str):
        """
        Setter for this ptp-parameter value
        """
        self.value = value

    def get_value(self) -> str:
        """
        Getter for this ptp-parameter value
        """
        return self.value

    
    