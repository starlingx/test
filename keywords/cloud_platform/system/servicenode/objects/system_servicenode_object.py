class SystemServicenodeObject:
    """
    This class represents a servicenode as an object.
    This is typically a line in the system servicenode output table.
    """

    def __init__(self):
        self.id:str = None
        self.name:str = None
        self.administrative:str = None
        self.operational:str = None
        self.availability:str = None
        self.ready_state: str = None
        self.administrative_state: str = None
        self.availability_status: str = None
        self.operational_state: str = None

    def set_id(self, host_id: str):
        """
        Setter for the host_id
        """
        self.id = host_id

    def get_id(self) -> str:
        """
        Getter for this id
        """
        return self.id

    def set_name(self, name: str):
        """
        Setter for the name
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for name
        """
        return self.name

    def set_administrative(self, administrative: str):
        """
        Setter for the administrative
        """
        self.administrative = administrative

    def get_administrative(self) -> str:
        """
        Getter for the administrative
        """
        return self.administrative

    def set_operational(self, operational: str):
        """
        Setter for the operational
        """
        self.operational = operational

    def get_operational(self) -> str:
        """
        Getter for the operational
        """
        return self.operational

    def set_availability(self, availability: str):
        """
        Setter for the availability
        """
        self.availability = availability

    def get_availability(self) -> str:
        """
        Getter for the availability
        """
        return self.availability

    def set_ready_state(self, ready_state: str):
        """
        Setter for the ready_state
        """
        self.ready_state = ready_state

    def get_ready_state(self) -> str:
        """
        Getter for the ready_state
        """
        return self.ready_state

    def set_administrative_state(self, administrative_state: str):
        """
        Setter for the administrative_state
        """
        self.administrative_state = administrative_state

    def get_administrative_state(self) -> str:
        """
        Getter for the administrative_state
        """
        return self.administrative_state

    def set_availability_status(self, availability_status):
        """
        Setter for availability_status
        """
        self.availability_status = availability_status

    def get_availability_status(self) -> str:
        """
        Getter for availability_status
        """
        return self.availability_status

    def set_operational_state(self, operational_state: str):
        """
        Setter for the operational_state
        """
        self.operational_state = operational_state

    def get_operational_state(self) -> str:
        """
        Getter for the operational_state
        """
        return self.operational_state
