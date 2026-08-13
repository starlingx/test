"""Object class for host LVG."""


class HostLvgObject:
    """Represents a host logical volume group."""

    def __init__(self):
        """Initialize HostLvgObject."""
        self.uuid: str = None
        self.lvm_vg_name: str = None
        self.vg_state: str = None

    def set_uuid(self, uuid: str):
        """Set the UUID.

        Args:
            uuid (str): The LVG UUID.
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """Get the UUID.

        Returns:
            str: The LVG UUID.
        """
        return self.uuid

    def set_lvm_vg_name(self, lvm_vg_name: str):
        """Set the LVM VG name.

        Args:
            lvm_vg_name (str): The volume group name.
        """
        self.lvm_vg_name = lvm_vg_name

    def get_lvm_vg_name(self) -> str:
        """Get the LVM VG name.

        Returns:
            str: The volume group name.
        """
        return self.lvm_vg_name

    def set_vg_state(self, vg_state: str):
        """Set the VG state.

        Args:
            vg_state (str): The volume group state.
        """
        self.vg_state = vg_state

    def get_vg_state(self) -> str:
        """Get the VG state.

        Returns:
            str: The volume group state.
        """
        return self.vg_state
