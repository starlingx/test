

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
        self.lvm_pv_uuid: str = None
        self.lvm_pv_size_gib: float = -1.0
        self.lvm_pe_total: int = -1
        self.lvm_pe_alloced: int = -1
        self.created_at: str = None
        self.updated_at: str = None


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

    def set_lvm_pv_uuid(self, lvm_pv_uuid):
        """
        Setter for the lvm_pv_uuid
        """
        self.lvm_pv_uuid = lvm_pv_uuid

    def get_lvm_pv_uuid(self) -> str:
        """
        Getter for the lvm_pv_uuid
        """
        return self.lvm_pv_uuid

    def set_lvm_pv_size_gib(self, lvm_pv_size_gib):
        """
        Setter for the lvm_pv_size_gib
        """
        self.lvm_pv_size_gib = lvm_pv_size_gib

    def get_lvm_pv_size_gib(self) -> float:
        """
        Getter for the lvm_pv_size_gib
        """
        return self.lvm_pv_size_gib

    def set_lvm_pe_total(self, lvm_pe_total):
        """
        Setter for the lvm_pe_total
        """
        self.lvm_pe_total = lvm_pe_total

    def get_lvm_pe_total(self) -> int:
        """
        Getter for the lvm_pe_total
        """
        return self.lvm_pe_total

    def set_lvm_pe_alloced(self, lvm_pe_alloced):
        """
        Setter for the lvm_pe_alloced
        """
        self.lvm_pe_alloced = lvm_pe_alloced

    def get_lvm_pe_alloced(self) -> int:
        """
        Getter for the lvm_pe_total
        """
        return self.lvm_pe_alloced

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