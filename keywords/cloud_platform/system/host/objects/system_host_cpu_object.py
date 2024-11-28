class SystemHostCPUObject:
    """
    This class represents a Host CPU as an object.
    This is typically a line in the system host-cpu-list output table.
    """

    def __init__(self, uuid: str):
        self.uuid: str = uuid
        self.log_core: int = -1
        self.processor: int = -1
        self.phy_core: int = -1
        self.thread: int = -1
        self.processor_model: str = None
        self.assigned_function: str = None
        self.processor_family: int = -1
        self.capabilities: dict = None
        self.ihost_uuid: str = None
        self.inode_uuid: str = None
        self.created_at: str = None
        self.updated_at: str = None

    def get_uuid(self) -> str:
        """
        Getter for this CPU's UUID
        """
        return self.uuid

    def set_log_core(self, log_core: int):
        """
        Setter for the log_cores
        """
        self.log_core = log_core

    def get_log_core(self) -> int:
        """
        Getter for the log_cores
        """
        return self.log_core

    def set_processor(self, processor: int):
        """
        Setter for the processor
        """
        self.processor = processor

    def get_processor(self) -> int:
        """
        Getter for the processor count
        """
        return self.processor

    def set_phy_core(self, phy_core: int):
        """
        Setter for the phy_core
        """
        self.phy_core = phy_core

    def get_phy_core(self) -> int:
        """
        Getter for the number of physical cores
        """
        return self.phy_core

    def set_thread(self, thread: int):
        """
        Setter for the thread id assigned to this CPU.
        """
        self.thread = thread

    def get_thread(self) -> int:
        """
        Getter for the id of the thread assigned to this CPU.
        """
        return self.thread

    def set_processor_model(self, processor_model: str):
        """
        Setter for the processor_model
        """
        self.processor_model = processor_model

    def get_processor_model(self) -> str:
        """
        Getter for the processor_model
        """
        return self.processor_model

    def set_processor_family(self, processor_family: int):
        """
        Setter for the processor family
        """
        self.processor_family = processor_family

    def get_processor_family(self) -> int:
        """
        Getter for the processor family
        """
        return self.processor_family

    def set_assigned_function(self, assigned_function: str):
        """
        Setter for the assigned_function
        """
        self.assigned_function = assigned_function

    def get_assigned_function(self) -> str:
        """
        Getter for the assigned_function
        """
        return self.assigned_function

    def set_capabilities(self, capabilities: str):
        """
        Setter for the port's capabilities
        """
        self.capabilities = capabilities

    def get_capabilities(self) -> str:
        """
        Getter for this port's capabilities
        """
        return self.capabilities

    def set_ihost_uuid(self, ihost_uuid: str):
        """
        Setter for host uuid
        """
        self.ihost_uuid = ihost_uuid

    def get_ihost_uuid(self) -> str:
        """
        Getter for the host uuid
        """
        return self.ihost_uuid

    def set_inode_uuid(self, inode_uuid: str):
        """
        Setter for inode uuid
        """
        self.inode_uuid = inode_uuid

    def get_inode_uuid(self) -> str:
        """
        Getter for the inode uuid
        """
        return self.inode_uuid

    def set_created_at(self, created_at: str):
        """
        Setter for created_at
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """
        Getter for the created_at
        """
        return self.created_at

    def set_updated_at(self, updated_at: str):
        """
        Setter for updated_at
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """
        Getter for the updated_at
        """
        return self.updated_at
