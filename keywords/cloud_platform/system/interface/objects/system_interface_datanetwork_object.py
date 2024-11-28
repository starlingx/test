class SystemInterfaceDatanetworkObject:
    """
    This class represents a Host Interface Datanetwork as an object.
    This is typically a line in the system interface-datanetwork-list output table.
    """

    def __init__(self):
        self.hostname: str = None
        self.uuid: str = None
        self.ifname: str = None
        self.datanetwork_name: str = None

    def set_hostname(self, hostname: str):
        """
        Setter for the hostname
        """
        self.hostname = hostname

    def get_hostname(self) -> str:
        """
        Getter for hostname
        Returns: the hostname

        """
        return self.hostname

    def get_name(self) -> str:
        """
        Getter for hostname
        """
        return self.hostname

    def set_uuid(self, uuid: str):
        """
        Setter for the uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for this if's uuid
        """
        return self.uuid

    def set_ifname(self, ifname: str):
        """
        Setter for the ifname
        """
        self.ifname = ifname

    def get_ifname(self) -> str:
        """
        Getter for this ifname
        """
        return self.ifname

    def set_datanetwork_name(self, datanetwork_name: str):
        """
        Setter for the datanetwork_name
        """
        self.datanetwork_name = datanetwork_name

    def get_datanetwork_name(self) -> str:
        """
        Getter for this datanetwork_name
        """
        return self.datanetwork_name
