class SystemServiceObject:
    """
    This class represents a service as an object.
    This is typically a line in the system service output table.
    """

    def __init__(self):
        self.id:int = -1
        self.service_name:str = None
        self.hostname:str = None
        self.state:str = None


    def set_id(self, service_id: int):
        """
        Setter for the service_id
        """
        self.id = service_id

    def get_id(self) -> int:
        """
        Getter for this id
        """
        return self.id

    def set_service_name(self, service_name: str):
        """
        Setter for the service_name
        """
        self.service_name = service_name

    def get_service_name(self) -> str:
        """
        Getter for service_name
        """
        return self.service_name

    def set_hostname(self, hostname: str):
        """
        Setter for the hostname
        """
        self.hostname = hostname

    def get_hostname(self) -> str:
        """
        Getter for the hostname
        """
        return self.hostname

    def set_state(self, state: str):
        """
        Setter for the state
        """
        self.state = state

    def get_state(self) -> str:
        """
        Getter for the state
        """
        return self.state
