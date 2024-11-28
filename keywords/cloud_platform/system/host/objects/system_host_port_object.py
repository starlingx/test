class SystemHostPortObject:
    """
    This class represents a Host Port as an object.
    This is typically a line in the system host-port-list output table.
    """

    def __init__(self):
        self.uuid = None
        self.name = None
        self.port_type = None
        self.pci_address = None
        self.device = -1
        self.processor = -1
        self.accelerated = False
        self.device_type = None

    def set_uuid(self, uuid: str):
        """
        Setter for the port's uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for this port's uuid
        """
        return self.uuid

    def set_name(self, name: str):
        """
        Setter for the port's name
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for this port's name
        """
        return self.name

    def set_port_type(self, port_type: str):
        """
        Setter for the port's type
        """
        self.port_type = port_type

    def get_port_type(self) -> str:
        """
        Getter for this port's type
        """
        return self.port_type

    def set_pci_address(self, pci_address: str):
        """
        Setter for the port's pci_address
        """
        self.pci_address = pci_address

    def get_pci_address(self) -> str:
        """
        Getter for this port's pci_address
        """
        return self.pci_address

    def set_device(self, device: int):
        """
        Setter for the port's device
        """
        self.device = device

    def get_device(self) -> int:
        """
        Getter for this port's device
        """
        return self.device

    def set_processor(self, processor: int):
        """
        Setter for the port's processor
        """
        self.processor = processor

    def get_processor(self) -> int:
        """
        Getter for this port's processor
        """
        return self.processor

    def set_accelerated(self, accelerated: bool):
        """
        Setter for the port's accelerated status
        """
        self.accelerated = accelerated

    def get_accelerated(self) -> bool:
        """
        Getter for this port's accelerated status
        """
        return self.accelerated

    def set_device_type(self, device_type: str):
        """
        Setter for the port's device type
        """
        self.device_type = device_type

    def get_device_type(self) -> str:
        """
        Getter for this port's device type
        """
        return self.device_type
