class SystemHostInterfaceObject:
    """
    System Host Interface Object
    """

    def __init__(self):
        self.ifname: str = None
        self.iftype: str = None
        self.ports: str = None
        self.imac: str = None
        self.imtu: int = None
        self.ifclass: str = None
        self.ptp_role: str = None
        self.aemode: str = None
        self.schedpolicy: str = None
        self.txhashpolicy: str = None
        self.primary_reselect: str = None
        self.uuid: str = None
        self.ihost_uuid: str = None
        self.vlan_id: str = None
        self.uses: str = None
        self.used_by: str = None
        self.created_at: str = None
        self.updated_at: str = None
        self.sriov_numvfs: int = 0
        self.sriov_vf_driver = None
        self.max_tx_rate = None
        self.accelerated = None

    def set_ifname(self, ifname: str):
        """
        Setter for ifname
        Args:
            ifname (): the ifname

        Returns:

        """
        self.ifname = ifname

    def get_ifname(self) -> str:
        """
        Getter for ifname
        Returns:

        """
        return self.ifname

    def set_iftype(self, iftype: str):
        """
        Setter for iftype
        Args:
            iftype (): the iftype

        Returns:

        """
        self.iftype = iftype

    def get_iftype(self) -> str:
        """
        Getter for iftype
        Returns:

        """
        return self.iftype

    def set_ports(self, ports: str):
        """
        Setter for ports
        Args:
            ports (): the ports

        Returns:

        """
        self.ports = ports

    def get_ports(self) -> str:
        """
        Getter for ports
        Returns:

        """
        return self.ports

    def set_imac(self, imac: str):
        """
        Setter for imac
        Args:
            imac (): the imac

        Returns:

        """
        self.imac = imac

    def get_imac(self) -> str:
        """
        Getter for imac
        Returns:

        """
        return self.imac

    def set_imtu(self, imtu: int):
        """
        Setter for imtu
        Args:
            imtu (): the imtu

        Returns:

        """
        self.imtu = imtu

    def get_imtu(self) -> int:
        """
        Getter for imtu
        Returns:

        """
        return self.imtu

    def set_ifclass(self, ifclass: str):
        """
        Setter for ifclass
        Args:
            ifclass (): the ifclass

        Returns:

        """
        self.ifclass = ifclass

    def get_ifclass(self) -> str:
        """
        Getter for ifclass
        Returns:

        """
        return self.ifclass

    def set_ptp_role(self, ptp_role: str):
        """
        Setter for ptp_role
        Args:
            ptp_role (): the ptp_role

        Returns:

        """
        self.ptp_role = ptp_role

    def get_ptp_role(self) -> str:
        """
        Getter for ptp_role
        Returns:

        """
        return self.ptp_role

    def set_aemode(self, aemode: str):
        """
        Setter for aemode
        Args:
            aemode (): the aemode

        Returns:

        """
        self.aemode = aemode

    def get_aemode(self) -> str:
        """
        Getter for aemode
        Returns: the aemode

        """
        return self.aemode

    def set_schedpolicy(self, schedpolicy: str):
        """
        Setter for schedpolicy
        Args:
            schedpolicy (): the schedpolicy

        Returns:

        """
        self.schedpolicy = schedpolicy

    def get_schedpolicy(self) -> str:
        """
        Getter for schedpolicy
        Returns: the schedpolicy

        """
        return self.schedpolicy

    def set_txhashpolicy(self, txhashpolicy: str):
        """
        Setter for txhashpolicy
        Args:
            txhashpolicy (): the txhashpolicy

        Returns:

        """
        self.txhashpolicy = txhashpolicy

    def get_txhashpolicy(self) -> str:
        """
        Getter for txhashpolicy
        Returns: the txhashpolicy

        """
        return self.txhashpolicy

    def set_primary_reselect(self, primary_reselect: str):
        """
        Setter for primary_reselect
        Args:
            primary_reselect (): the primary_reselect

        Returns:

        """
        self.primary_reselect = primary_reselect

    def get_primary_reselect(self) -> str:
        """
        Getter for primary_reselect
        Returns: the primary_reselect

        """
        return self.primary_reselect

    def set_uuid(self, uuid: str):
        """
        Setter for uuid
        Args:
            uuid (): the uuid

        Returns:

        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for uuid
        Returns: the uuid

        """
        return self.uuid

    def set_ihost_uuid(self, ihost_uuid: str):
        """
        Setter for ihost_uuid
        Args:
            ihost_uuid (): the ihost_uuid

        Returns:

        """
        self.ihost_uuid = ihost_uuid

    def get_ihost_uuid(self) -> str:
        """
        Getter for ihost_uuid
        Returns: the ihost_uuid

        """
        return self.ihost_uuid

    def set_vlan_id(self, vlan_id: str):
        """
        Setter for vlan_id
        Args:
            vlan_id (): the vlan_id

        Returns:

        """
        self.vlan_id = vlan_id

    def get_vlan_id(self) -> str:
        """
        Getter for vlan_id
        Returns: the vlan_id

        """
        return self.vlan_id

    def set_uses(self, uses: str):
        """
        Getter for uses
        Args:
            uses (): the uses value

        Returns:

        """
        self.uses = uses

    def get_uses(self) -> str:
        """
        Getter for uses
        Returns: the uses

        """
        return self.uses

    def set_used_by(self, used_by: str):
        """
        Setter for used_by
        Args:
            used_by (): the used_by value

        Returns:

        """
        self.used_by = used_by

    def get_used_by(self) -> str:
        """
        Getter for used_by
        Returns: the used_by

        """
        return self.used_by

    def set_created_at(self, created_at: str):
        """
        Setter for created at
        Args:
            created_at (): created at value

        Returns:

        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """
        Getter for created at
        Returns: created at

        """
        return self.created_at

    def set_updated_at(self, updated_at: str):
        """
        Setter for updated_at
        Args:
            updated_at (): the updated_at value

        Returns:

        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """
        Getter for updated_at
        Returns: the updated_at value

        """
        return self.updated_at

    def set_sriov_numvfs(self, sriov_numvfs: int):
        """
        Setter for sriov_numvfs
        Args:
            sriov_numvfs (): the sriov_numvfs

        Returns:

        """
        self.sriov_numvfs = sriov_numvfs

    def get_sriov_numvfs(self) -> int:
        """
        Getter for sriov_numvfs
        Returns:

        """
        return self.sriov_numvfs

    def set_sriov_vf_driver(self, sriov_vf_driver: str):
        """
        Setter for sriov_vf_driver
        Args:
            sriov_vf_driver (): the sriov_vf_driver

        Returns:

        """
        self.sriov_vf_driver = sriov_vf_driver

    def get_sriov_vf_driver(self) -> str:
        """
        Getter for sriov_vf_driver
        Returns: the sriov_vf_driver

        """
        return self.sriov_vf_driver

    def set_max_tx_rate(self, max_tx_rate: str):
        """
        Setter for max_tx_rate
        Args:
            max_tx_rate (): the max_tx_rate

        Returns:

        """
        self.max_tx_rate = max_tx_rate

    def get_max_tx_rate(self) -> str:
        """
        Getter for max_tx_rate
        Returns: the max_tx_rate

        """
        return self.max_tx_rate

    def set_accelerated(self, accelerated: str):
        """
        Setter for accelerated
        Args:
            accelerated (): accelerated value

        Returns:

        """
        self.accelerated = accelerated

    def get_accelerated(self) -> str:
        """
        Getter for accelerated
        Returns: the accelerated value

        """
        return self.accelerated
