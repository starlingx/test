class SystemHostPortShowObject:
    """
    This class represents a Host Port as an object.
    This is typically a line in the system host-port-show output table.
    """

    def __init__(self):
        self.name = None
        self.name_display = None
        self.type = None
        self.pciaddr = None
        self.dev_id = -1
        self.processor = -1
        self.sriov_totalvfs = None
        self.sriov_numvfs = -1
        self.sriov_vfs_pci_address = None
        self.sriov_vf_driver = None
        self.sriov_vf_pdevice_id = None
        self.driver = None
        self.pclass = None
        self.pvendor = None
        self.pdevice = None
        self.capabilities = None
        self.uuid = None
        self.host_uuid = None
        self.interface_uuid = None
        self.accelerated = None
        self.created_at = None
        self.updated_at = None
        self.capabilities = None

    def set_name(self, name: str):
        """
        Setter for the port's name
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for this port's name
        """
        return self.name

    def set_name_display(self, name_display: str):
        """
        Setter for the port's namedisplay
        """
        self.name_display = name_display

    def get_name_display(self) -> str:
        """
        Getter for this port's namedisplay
        """
        return self.name_display

    def set_type(self, port_type: str):
        """
        Setter for the port's type
        """
        self.type = port_type

    def get_type(self) -> str:
        """
        Getter for this port's type
        """
        return self.type

    def set_pciaddr(self, pciaddr: str):
        """
        Setter for the port's pciaddr
        """
        self.pciaddr = pciaddr

    def get_pciaddr(self) -> str:
        """
        Getter for this port's pciaddr
        """
        return self.pciaddr

    def set_dev_id(self, dev_id: int):
        """
        Setter for the port's dev_id
        """
        self.dev_id = dev_id

    def get_dev_id(self) -> int:
        """
        Getter for this port's dev_id
        """
        return self.dev_id

    def set_processor(self, processor: int):
        """
        Setter for the port's processor
        """
        self.processor = processor

    def get_processor(self) -> int:
        """
        Getter for this port's processor
        """
        return self.processor

    def set_sriov_totalvfs(self, sriov_totalvfs: str):
        """
        Setter for the port's sriov_totalvfs
        """
        self.sriov_totalvfs = sriov_totalvfs

    def get_sriov_totalvfs(self) -> str:
        """
        Getter for this port's sriov_totalvfs
        """
        return self.sriov_totalvfs

    def set_sriov_numvfs(self, sriov_numvfs: int):
        """
        Setter for the port's sriov_numvfs
        """
        self.sriov_numvfs = sriov_numvfs

    def get_sriov_numvfs(self) -> int:
        """
        Getter for this port's sriov_numvfs
        """
        return self.sriov_numvfs

    def set_sriov_vfs_pci_address(self, sriov_vfs_pci_address: str):
        """
        Setter for the port's sriov_vfs_pci_address
        """
        self.sriov_vfs_pci_address = sriov_vfs_pci_address

    def get_sriov_vfs_pci_address(self) -> str:
        """
        Getter for this port's sriov_vfs_pci_address
        """
        return self.sriov_vfs_pci_address

    def set_sriov_vf_driver(self, sriov_vf_driver: str):
        """
        Setter for the port's sriov_vf_driver
        """
        self.sriov_vf_driver = sriov_vf_driver

    def get_sriov_vf_driver(self) -> str:
        """
        Getter for this port's sriov_vf_driver
        """
        return self.sriov_vf_driver

    def set_sriov_vf_pdevice_id(self, sriov_vf_pdevice_id: str):
        """
        Setter for the port's sriov_vf_pdevice_id
        """
        self.sriov_vf_pdevice_id = sriov_vf_pdevice_id

    def get_sriov_vf_pdevice_id(self) -> str:
        """
        Getter for this port's sriov_vf_pdevice_id
        """
        return self.sriov_vf_pdevice_id

    def set_driver(self, driver: str):
        """
        Setter for the port's driver
        """
        self.driver = driver

    def get_driver(self) -> str:
        """
        Getter for this port's driver
        """
        return self.driver

    def set_pclass(self, pclass: str):
        """
        Setter for the port's pclass
        """
        self.pclass = pclass

    def get_pclass(self) -> str:
        """
        Getter for this port's pclass
        """
        return self.pclass

    def set_pvendor(self, pvendor: str):
        """
        Setter for the port's pvendor
        """
        self.pvendor = pvendor

    def get_pvendor(self) -> str:
        """
        Getter for this port's pvendor
        """
        return self.pvendor

    def set_pdevice(self, pdevice: str):
        """
        Setter for the port's pdevice
        """
        self.pdevice = pdevice

    def get_pdevice(self) -> str:
        """
        Getter for this port's pdevice
        """
        return self.pdevice

    def set_uuid(self, uuid: str):
        """
        Setter for the port's uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for this port's uuid
        """
        return self.uuid

    def set_host_uuid(self, host_uuid: str):
        """
        Setter for the port's host_uuid
        """
        self.host_uuid = host_uuid

    def get_host_uuid(self) -> str:
        """
        Getter for this port's host_uuid
        """
        return self.host_uuid

    def set_interface_uuid(self, interface_uuid: str):
        """
        Setter for the port's interface_uuid
        """
        self.interface_uuid = interface_uuid

    def get_interface_uuid(self) -> str:
        """
        Getter for this port's interface_uuid
        """
        return self.interface_uuid

    def set_accelerated(self, accelerated: bool):
        """
        Setter for the port's accelerated
        """
        self.accelerated = accelerated

    def get_accelerated(self) -> bool:
        """
        Getter for this port's accelerated
        """
        return self.accelerated

    def set_created_at(self, created_at: str):
        """
        Setter for the port's created_at
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """
        Getter for this port's created_at
        """
        return self.created_at

    def set_updated_at(self, updated_at: str):
        """
        Setter for the port's updated_at
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """
        Getter for this port's updated_at
        """
        return self.updated_at

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