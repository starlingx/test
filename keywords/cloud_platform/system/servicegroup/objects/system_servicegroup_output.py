class SystemServiceGroupObject:
    """
    This class represents a ServiceGroup as an object.
    This is typically a line in the system systemgroup-list output table.
    """

    def __init__(self, service_group_name: str):

        self.service_group_name: str = service_group_name
        self.uuid: str = None
        self.hostname: str = None
        self.state: str = None

    def service_group_name(self) -> str:
        """
        Getter for this ServiceGroup's Name
        """
        return self.service_group_name()

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
