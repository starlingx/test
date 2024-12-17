

class SystemHostLvgObject:

    """
    This class represents system host-lvg as an object.
    """

    def __init__(self):
        self.uuid: str = None
        self.lvg_name: str = None
        self.state: str = None
        self.access: str = None
        self.total_size: float = -1.0
        self.avail_size: float = -1.0
        self.current_pvs: int = -1
        self.current_lvs: int = -1
        self.ihost_uuid : str = None
        self.lvm_max_lv: int = -1
        self.lvm_max_pv: int = -1
        self.lvm_vg_size_gib: float = -1.0
        self.lvm_vg_total_pe: int = -1
        self.lvm_vg_free_pe: int = -1
        self.created_at: str = None
        self.updated_at: str = None
        self.parameters = {}


    def set_uuid(self, uuid):
        """
        Setter for host-lvg uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for host-lvg UUID
        """
        return self.uuid

    def set_lvg_name(self, lvg_name):
        """
        Setter for the lvg_name
        """
        self.lvg_name = lvg_name

    def get_lvg_name(self) -> str:
        """
        Getter for the lvg_name
        """
        return self.lvg_name

    def set_state(self, state):
        """
        Setter for the state
        """
        self.state = state

    def get_state(self) -> str:
        """
        Getter for the state
        """
        return self.state

    def set_access(self, access):
        """
        Setter for access
        """
        self.access = access

    def get_access(self) -> str:
        """
        Getter for access
        """
        return self.access

    def set_total_size(self, total_size):
        """
        Setter for total_size
        """
        self.total_size = total_size

    def get_total_size(self) -> float:
        """
        Getter for total_size
        """
        return self.total_size

    def set_avail_size(self, avail_size):
        """
        Setter for avail_size
        """
        self.avail_size = avail_size

    def get_avail_size(self) -> float:
        """
        Getter for avail_size
        """
        return self.avail_size

    def set_current_pvs(self, current_pvs):
        """
        Setter for current_pvs
        """
        self.current_pvs = current_pvs

    def get_current_pvs(self) -> int:
        """
        Getter for current_pvs
        """
        return self.current_pvs

    def set_current_lvs(self, current_lvs):
        """
        Setter for current_lvs
        """
        self.current_lvs = current_lvs

    def get_current_lvs(self) -> int:
        """
        Getter for current_lvs
        """
        return self.current_lvs

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

    def set_lvm_max_lv(self, lvm_max_lv):
        """
        Setter for lvm_max_lv
        """
        self.lvm_max_lv = lvm_max_lv

    def get_lvm_max_lv(self) -> int:
        """
        Getter for lvm_max_lv
        """
        return self.lvm_max_lv

    def set_lvm_max_pv(self, lvm_max_pv):
        """
        Setter for lvm_max_pv
        """
        self.lvm_max_pv = lvm_max_pv

    def get_lvm_max_pv(self) -> int:
        """
        Getter for lvm_max_pv
        """
        return self.lvm_max_pv

    def set_lvm_vg_size_gib(self, lvm_vg_size_gib):
        """
        Setter for lvm_vg_size_gib
        """
        self.lvm_vg_size_gib = lvm_vg_size_gib

    def get_lvm_vg_size_gib(self) -> float:
        """
        Getter for lvm_vg_size_gib
        """
        return self.lvm_vg_size_gib

    def set_lvm_vg_total_pe(self, lvm_vg_total_pe):
        """
        Setter for lvm_vg_total_pe
        """
        self.lvm_vg_total_pe = lvm_vg_total_pe

    def get_lvm_vg_total_pe(self) -> int:
        """
        Getter for lvm_vg_total_pe
        """
        return self.lvm_vg_total_pe

    def set_lvm_vg_free_pe(self, lvm_vg_free_pe):
        """
        Setter for lvm_vg_free_pe
        """
        self.lvm_vg_free_pe = lvm_vg_free_pe

    def get_lvm_vg_free_pe(self) -> int:
        """
        Getter for lvm_vg_free_pe
        """
        return self.lvm_vg_free_pe

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

    def set_parameters(self, parameters):
        """
        Setter for host-lvg parameters
        """
        self.parameters = parameters

    def get_parameters(self) -> dict:
        """
        Getter for host-lvg parameters
        """
        return self.parameters