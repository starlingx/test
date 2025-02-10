class SystemPTPInterfaceObject:
    """
    Represents a SystemPTPInterfaceObject with associated attributes.
    """

    def __init__(self):
        """
        Initializes a SystemPTPInterfaceObject instance.
        """
        self.uuid = None
        self.name = None
        self.interface_names = []
        self.ptp_instance_name = None
        self.parameters = []


    def set_uuid(self, uuid: str):
        """
        Setter for this ptp-interface uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for this ptp-interface uuid
        """
        return self.uuid

    def set_name(self, name: str):
        """
        Setter for this ptp-interface name
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for this ptp-interface name
        """
        return self.name

    def set_interface_names(self, interface_names: list):
        """
        Setter for this ptp-interface interface_names
        """
        self.interface_names = interface_names

    def get_interface_names(self) -> list[str]:
        """
        Getter for this ptp-interface interface_names
        """
        return self.interface_names

    def set_ptp_instance_name(self, ptp_instance_name: str):
        """
        Setter for this ptp-interface ptp_instance_name
        """
        self.ptp_instance_name = ptp_instance_name

    def get_ptp_instance_name(self) -> str:
        """
        Getter for this ptp-interface ptp_instance_name
        """
        return self.ptp_instance_name

    def set_parameters(self, parameters: list):
        """
        Setter for this ptp-interface parameters
        """
        self.parameters = parameters

    def get_parameters(self) -> list[str]:
        """
        Getter for this ptp-interface parameters
        """
        return self.parameters
    
    