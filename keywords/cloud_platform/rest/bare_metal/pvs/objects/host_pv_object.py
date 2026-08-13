"""Object class for host physical volume."""


class HostPvObject:
    """Represents a host physical volume."""

    def __init__(self):
        """Initialize HostPvObject."""
        self.uuid: str = None
        self.pv_state: str = None
        self.pv_type: str = None

    def set_uuid(self, uuid: str):
        """Set the UUID.

        Args:
            uuid (str): The PV UUID.
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """Get the UUID.

        Returns:
            str: The PV UUID.
        """
        return self.uuid

    def set_pv_state(self, pv_state: str):
        """Set the PV state.

        Args:
            pv_state (str): The physical volume state.
        """
        self.pv_state = pv_state

    def get_pv_state(self) -> str:
        """Get the PV state.

        Returns:
            str: The physical volume state.
        """
        return self.pv_state

    def set_pv_type(self, pv_type: str):
        """Set the PV type.

        Args:
            pv_type (str): The physical volume type.
        """
        self.pv_type = pv_type

    def get_pv_type(self) -> str:
        """Get the PV type.

        Returns:
            str: The physical volume type.
        """
        return self.pv_type
