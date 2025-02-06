class SystemHostIfPTPListObject:
    """
    Represents a SystemHostIfPTPListObject with associated attributes.
    """

    def __init__(self):
        """
        Initializes a SystemHostIfPTPListObject instance.
        """
        self.uuid = None
        self.ptp_instance_name = None
        self.interface_names = []

    def set_uuid(self, uuid: str):
        """
        Setter for this host-if-ptp-list uuid
        """
        self.uuid = uuid
    
    def get_uuid(self) -> str:
        """
        Getter for this host-if-ptp-list uuid
        """
        return self.uuid

    def set_ptp_instance_name(self, ptp_instance_name: str):
        """
        Setter for this host-if-ptp-list PTP instance name
        """
        self.ptp_instance_name = ptp_instance_name

    def get_ptp_instance_name(self) -> str:
        """
        Getter for this host-if-ptp-list PTP instance name
        """
        return self.ptp_instance_name
    
    def set_interface_names(self, interface_names: list):
        """
        Setter for this host-if-ptp-list interface_names
        """
        self.interface_names = interface_names

    def get_interface_names(self) -> list[str]:
        """
        Getter for this host-if-ptp-list interface_names
        """
        return self.interface_names


