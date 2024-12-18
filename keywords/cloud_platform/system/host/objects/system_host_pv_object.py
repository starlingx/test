

class SystemHostPvObject:

    """
    This class represents system host-pv as an object.
    """

    def __init__(self):
        self.uuid: str = None
        self.lvm_pv_name: str = None
        self.disk_or_part_uuid: str = None
        self.disk_or_part_device_node: str = None
        self.disk_or_part_device_path: str = None
        self.pv_state: str = None
        self.pv_type: str = None
        self.lvm_vg_name: str = None
        self.ihost_uuid : str = None


    def set_uuid(self, uuid):
        """
        Setter for host-pv uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for host-pv UUID
        """
        return self.uuid

    def set_lvm_pv_name(self, lvm_pv_name):
        """
        Setter for the lvm_pv_name
        """
        self.lvm_pv_name = lvm_pv_name

    def get_lvm_pv_name(self) -> str:
        """
        Getter for the lvm_pv_name
        """
        return self.lvm_pv_name

    def set_disk_or_part_uuid(self, disk_or_part_uuid):
        """
        Setter for the disk_or_part_uuid
        """
        self.disk_or_part_uuid = disk_or_part_uuid

    def get_disk_or_part_uuid(self) -> str:
        """
        Getter for the disk_or_part_uuid
        """
        return self.disk_or_part_uuid

    def set_disk_or_part_device_node(self, disk_or_part_device_node):
        """
        Setter for disk_or_part_device_node
        """
        self.disk_or_part_device_node = disk_or_part_device_node

    def get_disk_or_part_device_node(self) -> str:
        """
        Getter for disk_or_part_device_node
        """
        return self.disk_or_part_device_node

    def set_disk_or_part_device_path(self, disk_or_part_device_path):
        """
        Setter for disk_or_part_device_path
        """
        self.disk_or_part_device_path = disk_or_part_device_path

    def get_disk_or_part_device_path(self) -> str:
        """
        Getter for disk_or_part_device_path
        """
        return self.disk_or_part_device_path

    def set_pv_state(self, pv_state):
        """
        Setter for pv_state
        """
        self.pv_state = pv_state

    def get_pv_state(self) -> str:
        """
        Getter for pv_state
        """
        return self.pv_state

    def set_pv_type(self, pv_type):
        """
        Setter for pv_type
        """
        self.pv_type = pv_type

    def get_pv_type(self) -> str:
        """
        Getter for pv_type
        """
        return self.pv_type

    def set_lvm_vg_name(self, lvm_vg_name):
        """
        Setter for lvm_vg_name
        """
        self.lvm_vg_name = lvm_vg_name

    def get_lvm_vg_name(self) -> str:
        """
        Getter for lvm_vg_name
        """
        return self.lvm_vg_name

    def set_ihost_uuid(self, ihost_uuid):
        """
        Setter for host-lvg ihost_uuid
        """
        self.ihost_uuid = ihost_uuid

    def get_ihost_uuid(self) -> str:
        """
        Getter for host-lvg ihost_uuid
        """
        return self.ihost_uuid