class SystemHostIfPTPAssignObject:
    """
    Represents a SystemHostIfPTPAssignObject with associated attributes.
    """

    def __init__(self):
        """
        Initializes a SystemHostIfPTPAssignObject instance.
        """
        self.uuid = None
        self.name = None
        self.ptp_instance_name = None
        self.parameters = []


    def set_uuid(self, uuid: str):
        """
        Setter for this host-if-ptp-assign and host-if-ptp-remove uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for this host-if-ptp-assign and host-if-ptp-remove uuid
        """
        return self.uuid

    def set_name(self, name: str):
        """
        Setter for this host-if-ptp-assign and host-if-ptp-remove name
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for this host-if-ptp-assign and host-if-ptp-remove name
        """
        return self.name

    def set_ptp_instance_name(self, ptp_instance_name: str):
        """
        Setter for this host-if-ptp-assign and host-if-ptp-remove PTP instance name
        """
        self.ptp_instance_name = ptp_instance_name

    def get_ptp_instance_name(self) -> str:
        """
        Getter for this host-if-ptp-assign and host-if-ptp-remove PTP instance name
        """
        return self.ptp_instance_name
    
    def set_parameters(self, parameters: list):
        """
        Setter for this host-if-ptp-assign and host-if-ptp-remove parameters
        """
        self.parameters = parameters

    def get_parameters(self) -> list[str]:
        """
        Getter for this host-if-ptp-assign and host-if-ptp-remove parameters
        """
        return self.parameters


