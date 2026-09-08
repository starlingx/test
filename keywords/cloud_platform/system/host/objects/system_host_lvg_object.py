"""Module for the SystemHostLvgObject that represents a 'system host-lvg' entry."""


class SystemHostLvgObject:
    """This class represents system host-lvg as an object."""

    def __init__(self):
        """Initialize the SystemHostLvgObject with default values."""
        self.uuid: str = None
        self.lvg_name: str = None
        self.state: str = None
        self.access: str = None
        self.lvm_function: str = None
        self.lvm_type: str = None
        self.lvm_pool_size = None
        self.total_size: float = -1.0
        self.avail_size: float = -1.0
        self.current_pvs: int = -1
        self.current_lvs: int = -1
        self.ihost_uuid: str = None
        self.lvm_max_lv: int = -1
        self.lvm_max_pv: int = -1
        self.lvm_vg_size_gib: float = -1.0
        self.lvm_vg_total_pe: int = -1
        self.lvm_vg_free_pe: int = -1
        self.created_at: str = None
        self.updated_at: str = None
        self.parameters = {}

    def set_uuid(self, uuid):
        """Set the host-lvg uuid."""
        self.uuid = uuid

    def get_uuid(self) -> str:
        """Get the host-lvg UUID."""
        return self.uuid

    def set_lvg_name(self, lvg_name):
        """Set the lvg_name."""
        self.lvg_name = lvg_name

    def get_lvg_name(self) -> str:
        """Get the lvg_name."""
        return self.lvg_name

    def set_state(self, state):
        """Set the state."""
        self.state = state

    def get_state(self) -> str:
        """Get the state."""
        return self.state

    def set_access(self, access):
        """Set the access."""
        self.access = access

    def get_access(self) -> str:
        """Get the access."""
        return self.access

    def set_lvm_function(self, lvm_function):
        """Set the lvm_function."""
        self.lvm_function = lvm_function

    def get_lvm_function(self) -> str:
        """Get the lvm_function."""
        return self.lvm_function

    def set_lvm_type(self, lvm_type):
        """Set the lvm_type."""
        self.lvm_type = lvm_type

    def get_lvm_type(self) -> str:
        """Get the lvm_type."""
        return self.lvm_type

    def set_lvm_pool_size(self, lvm_pool_size):
        """Set the lvm_pool_size."""
        self.lvm_pool_size = lvm_pool_size

    def get_lvm_pool_size(self):
        """Get the lvm_pool_size."""
        return self.lvm_pool_size

    def set_total_size(self, total_size):
        """Set the total_size."""
        self.total_size = total_size

    def get_total_size(self) -> float:
        """Get the total_size."""
        return self.total_size

    def set_avail_size(self, avail_size):
        """Set the avail_size."""
        self.avail_size = avail_size

    def get_avail_size(self) -> float:
        """Get the avail_size."""
        return self.avail_size

    def set_current_pvs(self, current_pvs):
        """Set the current_pvs."""
        self.current_pvs = current_pvs

    def get_current_pvs(self) -> int:
        """Get the current_pvs."""
        return self.current_pvs

    def set_current_lvs(self, current_lvs):
        """Set the current_lvs."""
        self.current_lvs = current_lvs

    def get_current_lvs(self) -> int:
        """Get the current_lvs."""
        return self.current_lvs

    def set_ihost_uuid(self, ihost_uuid):
        """Set the host-lvg ihost_uuid."""
        self.ihost_uuid = ihost_uuid

    def get_ihost_uuid(self) -> str:
        """Get the host-lvg ihost_uuid."""
        return self.ihost_uuid

    def set_lvm_max_lv(self, lvm_max_lv):
        """Set the lvm_max_lv."""
        self.lvm_max_lv = lvm_max_lv

    def get_lvm_max_lv(self) -> int:
        """Get the lvm_max_lv."""
        return self.lvm_max_lv

    def set_lvm_max_pv(self, lvm_max_pv):
        """Set the lvm_max_pv."""
        self.lvm_max_pv = lvm_max_pv

    def get_lvm_max_pv(self) -> int:
        """Get the lvm_max_pv."""
        return self.lvm_max_pv

    def set_lvm_vg_size_gib(self, lvm_vg_size_gib):
        """Set the lvm_vg_size_gib."""
        self.lvm_vg_size_gib = lvm_vg_size_gib

    def get_lvm_vg_size_gib(self) -> float:
        """Get the lvm_vg_size_gib."""
        return self.lvm_vg_size_gib

    def set_lvm_vg_total_pe(self, lvm_vg_total_pe):
        """Set the lvm_vg_total_pe."""
        self.lvm_vg_total_pe = lvm_vg_total_pe

    def get_lvm_vg_total_pe(self) -> int:
        """Get the lvm_vg_total_pe."""
        return self.lvm_vg_total_pe

    def set_lvm_vg_free_pe(self, lvm_vg_free_pe):
        """Set the lvm_vg_free_pe."""
        self.lvm_vg_free_pe = lvm_vg_free_pe

    def get_lvm_vg_free_pe(self) -> int:
        """Get the lvm_vg_free_pe."""
        return self.lvm_vg_free_pe

    def set_created_at(self, created_at):
        """Set the host-lvg created_at."""
        self.created_at = created_at

    def get_created_at(self) -> str:
        """Get the host-lvg created_at."""
        return self.created_at

    def set_updated_at(self, updated_at):
        """Set the host-lvg updated_at."""
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """Get the host-lvg updated_at."""
        return self.updated_at

    def set_parameters(self, parameters):
        """Set the host-lvg parameters."""
        self.parameters = parameters

    def get_parameters(self) -> dict:
        """Get the host-lvg parameters."""
        return self.parameters

    def get_thin_cur_lv(self) -> int | None:
        """
        Get the current number of thin logical volumes provisioned in the volume group.

        The value comes from the already-parsed 'parameters' mapping of 'system host-lvg-show'
        (e.g. {'thin_cur_lv': 1}). Returns None when the key is absent, so callers can tell
        "unknown" apart from a genuine 0.

        Returns:
            int | None: the current number of thin logical volumes, or None if the key is not present.
        """
        if "thin_cur_lv" not in self.parameters:
            return None
        return int(self.parameters["thin_cur_lv"])
