

class SystemHostDiskPartitionObject:

    """
    This class represents system host-disk-partition as an object.
    """

    def __init__(self):
        self.uuid: str = None
        self.device_path: str = None
        self.device_node: str = None
        self.type_guid: str = None
        self.type_name: str = None
        self.size_gib: int = -1
        self.size_mib: int = -1
        self.start_mib: int = -1
        self.end_mib: int = -1
        self.status: str = None
        self.ihost_uuid : str = None
        self.idisk_uuid: str = None
        self.ipv_uuid: str = None
        self.created_at: str = None
        self.updated_at: str = None


    def set_uuid(self, uuid):
        """
        Setter for disk-partition uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for disk-partition uuid
        """
        return self.uuid

    def set_device_path(self, device_path):
        """
        Setter for the device_path
        """
        self.device_path = device_path

    def get_device_path(self) -> str:
        """
        Getter for the device_path
        """
        return self.device_path

    def set_device_node(self, device_node):
        """
        Setter for the device_node
        """
        self.device_node = device_node

    def get_device_node(self) -> str:
        """
        Getter for the device_node
        """
        return self.device_node

    def set_type_guid(self, type_guid):
        """
        Setter for type_guid
        """
        self.type_guid = type_guid

    def get_type_guid(self) -> str:
        """
        Getter for type_guid
        """
        return self.type_guid

    def set_type_name(self, type_name):
        """
        Setter for type_name
        """
        self.type_name = type_name

    def get_type_name(self) -> str:
        """
        Getter for type_name
        """
        return self.type_name

    def set_size_gib(self, size_gib):
        """
        Setter for size_gib
        """
        self.size_gib = size_gib

    def get_size_gib(self) -> int:
        """
        Getter for size_gib
        """
        return self.size_gib

    def set_size_mib(self, size_mib):
        """
        Setter for size_mib
        """
        self.size_mib = size_mib

    def get_size_mib(self) -> int:
        """
        Getter for size_mib
        """
        return self.size_mib

    def set_start_mib(self, start_mib):
        """
        Setter for start_mib
        """
        self.start_mib = start_mib

    def get_start_mib(self) -> int:
        """
        Getter for start_mib
        """
        return self.start_mib

    def set_end_mib(self, end_mib):
        """
        Setter for end_mib
        """
        self.end_mib = end_mib

    def get_end_mib(self) -> int:
        """
        Getter for end_mib
        """
        return self.end_mib

    def set_status(self, status):
        """
        Setter for status
        """
        self.status = status

    def get_status(self) -> str:
        """
        Getter for status
        """
        return self.status

    def set_ihost_uuid(self, ihost_uuid):
        """
        Setter for ihost_uuid
        """
        self.ihost_uuid = ihost_uuid

    def get_ihost_uuid(self) -> str:
        """
        Getter for ihost_uuid
        """
        return self.ihost_uuid

    def set_idisk_uuid(self, idisk_uuid):
        """
        Setter for the idisk_uuid
        """
        self.idisk_uuid = idisk_uuid

    def get_idisk_uuid(self) -> str:
        """
        Getter for the idisk_uuid
        """
        return self.idisk_uuid

    def set_ipv_uuid(self, ipv_uuid):
        """
        Setter for the ipv_uuid
        """
        self.ipv_uuid = ipv_uuid

    def get_ipv_uuid(self) -> float:
        """
        Getter for the ipv_uuid
        """
        return self.ipv_uuid

    def set_created_at(self, created_at):
        """
        Setter for host-lvg created_at
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """
        Getter for host-lvg created_at
        """
        return self.created_at

    def set_updated_at(self, updated_at):
        """
        Setter for host-lvg updated_at
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """
        Getter for host-lvg updated_at
        """
        return self.updated_at