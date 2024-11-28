class SystemHostDeviceObject:
    """
    This class represents a Host Device as an object.
    This is typically a line in the system host-device-list output table.
    """

    def __init__(self):
        self.address = None
        self.class_id = None
        self.class_name = None
        self.device_id = -1
        self.device_name = None
        self.enabled = False
        self.name = None
        self.numa_node = -1
        self.vendor_id = None
        self.vendor_name = None

    def set_address(self, address: str):
        """
        Setter for the device's address
        """
        self.address = address

    def get_address(self) -> str:
        """
        Getter for this device's address
        """
        return self.address

    def set_class_id(self, class_id: str):
        """
        Setter for the device's class id
        """
        self.class_id = class_id

    def get_class_id(self) -> str:
        """
        Getter for this device's class id
        """
        return self.class_id

    def set_class_name(self, class_name: str):
        """
        Setter for the device's class_name
        """
        self.class_name = class_name

    def get_class_name(self) -> str:
        """
        Getter for this device's class name
        """
        return self.class_name

    def set_device_id(self, device_id: int):
        """
        Setter for the device's id
        """
        self.device_id = device_id

    def get_device_id(self) -> int:
        """
        Getter for this device's id
        """
        return self.device_id

    def set_device_name(self, device_name: str):
        """
        Setter for the device's device name
        """
        self.device_name = device_name

    def get_device_name(self) -> str:
        """
        Getter for this device's device name
        """
        return self.device_name

    def set_enabled(self, enabled: bool):
        """
        Setter for the device's enabled status
        """
        self.enabled = enabled

    def get_enabled(self) -> bool:
        """
        Getter for this device's enabled status
        """
        return self.enabled

    def set_name(self, name: str):
        """
        Setter for the device's name
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for this device's name
        """
        return self.name

    def set_numa_node(self, numa_node: int):
        """
        Setter for the device's numa_node
        """
        self.numa_node = numa_node

    def get_numa_node(self) -> int:
        """
        Getter for this device's numa_node
        """
        return self.numa_node

    def set_vendor_id(self, vendor_id: str):
        """
        Setter for the device's vendor id
        """
        self.vendor_id = vendor_id

    def get_vendor_id(self) -> str:
        """
        Getter for this device's vendor id
        """
        return self.vendor_id

    def set_vendor_name(self, vendor_name: str):
        """
        Setter for the device's vendor name
        """
        self.vendor_name = vendor_name

    def get_vendor_name(self) -> str:
        """
        Getter for this device's vendor name
        """
        return self.vendor_name
