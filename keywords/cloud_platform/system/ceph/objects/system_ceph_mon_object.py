class SystemCephMonObject:
    """
    This class represents a Host Disk as an object.
    This is typically a line in the system ceph-mon output table.
    """

    def __init__(self):
        self.uuid:str = None
        self.ceph_mon_gib:int = -1
        self.hostname:str = None
        self.state:str = None
        self.task:str = None
        self.created_at: str = None
        self.updated_at: str = None

    def set_uuid(self, uuid: str):
        """
        Setter for the uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for this uuid
        """
        return self.uuid

    def set_ceph_mon_gib(self, ceph_mon_gib: int):
        """
        Setter for the ceph_mon_gib
        """
        self.ceph_mon_gib = ceph_mon_gib

    def get_ceph_mon_gib(self) -> int:
        """
        Getter for ceph_mon_gib
        """
        return self.ceph_mon_gib

    def set_hostname(self, hostname: str):
        """
        Setter for the hostname
        """
        self.hostname = hostname

    def get_hostname(self) -> str:
        """
        Getter for the hostname
        """
        return self.hostname

    def set_state(self, state: str):
        """
        Setter for the state
        """
        self.state = state

    def get_state(self) -> str:
        """
        Getter for the state
        """
        return self.state

    def set_task(self, task: str):
        """
        Setter for the task
        """
        self.task = task

    def get_task(self) -> str:
        """
        Getter for the task
        """
        return self.task

    def set_created_at(self, created_at):
        """
        Setter for created_at
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """
        Getter for created_at
        """
        return self.created_at

    def set_updated_at(self, updated_at):
        """
        Setter for updated_at
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """
        Getter for updated_at
        """
        return self.updated_at
