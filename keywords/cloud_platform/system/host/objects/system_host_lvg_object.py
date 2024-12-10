

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
