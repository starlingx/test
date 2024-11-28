class SystemHostDiskObject:
    """
    This class represents a Host Disk as an object.
    This is typically a line in the system host-disk-list output table.
    """

    def __init__(self):
        self.uuid = None
        self.device_node = None
        self.device_num = None
        self.device_type = None
        self.size_gib = 0.0
        self.available_gib = 0.0
        self.rpm = None
        self.serial_id = None
        self.device_path = None
        self.vendor_name = None

    def set_uuid(self, uuid: str):
        """
        Setter for the disk's uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for this disk's uuid
        """
        return self.uuid

    def set_device_node(self, device_node: str):
        """
        Setter for the disk's device_node
        """
        self.device_node = device_node

    def get_device_node(self) -> str:
        """
        Getter for this disk's device_node
        """
        return self.device_node

    def set_device_num(self, device_num: str):
        """
        Setter for the disk's device_num
        """
        self.device_num = device_num

    def get_device_num(self) -> str:
        """
        Getter for this disk's device_num
        """
        return self.device_num

    def set_device_type(self, device_type: str):
        """
        Setter for the disk's device_type
        """
        self.device_type = device_type

    def get_device_type(self) -> str:
        """
        Getter for this disk's device_type
        """
        return self.device_type

    def set_size_gib(self, size_gib: float):
        """
        Setter for the disk's size_gib
        """
        self.size_gib = size_gib

    def get_size_gib(self) -> float:
        """
        Getter for this disk's size_gib
        """
        return self.size_gib

    def set_available_gib(self, available_gib: float):
        """
        Setter for the disk's available_gib
        """
        self.available_gib = available_gib

    def get_available_gib(self) -> float:
        """
        Getter for this disk's available_gib
        """
        return self.available_gib

    def set_rpm(self, rpm: str):
        """
        Setter for the disk's rpm
        """
        self.rpm = rpm

    def get_rpm(self) -> str:
        """
        Getter for this disk's rpm
        """
        return self.rpm

    def set_serial_id(self, serial_id: str):
        """
        Setter for the disk's serial_id
        """
        self.serial_id = serial_id

    def get_serial_id(self) -> str:
        """
        Getter for this disk's serial_id
        """
        return self.serial_id

    def set_device_path(self, device_path: str):
        """
        Setter for the disk's device_path
        """
        self.device_path = device_path

    def get_device_path(self) -> str:
        """
        Getter for this disk's device_path
        """
        return self.device_path
