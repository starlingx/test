class SystemServiceParameterObject:
    """
    Class to represent a single service parameter from the service parameter list output.
    """

    def __init__(self):
        """
        Constructor.
        """
        self.service = None
        self.section = None
        self.name = None
        self.value = None

    def set_service(self, service: str):
        """Setter for service"""
        self.service = service

    def get_service(self) -> str:
        """Getter for service"""
        return self.service

    def set_section(self, section: str):
        """Setter for section"""
        self.section = section

    def get_section(self) -> str:
        """Getter for section"""
        return self.section

    def set_name(self, name: str):
        """Setter for name"""
        self.name = name

    def get_name(self) -> str:
        """Getter for name"""
        return self.name

    def set_value(self, value: str):
        """Setter for value"""
        self.value = value

    def get_value(self) -> str:
        """Getter for value"""
        return self.value
