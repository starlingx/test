"""OpenStack hypervisor list data object."""


class OpenStackHypervisorListObject:
    """Object to represent the output of the 'openstack hypervisor list' command."""

    def __init__(self):
        """Initialize OpenStackHypervisorListObject."""
        self.id = None
        self.hypervisor_hostname = None
        self.hypervisor_type = None
        self.host_ip = None
        self.state = None

    def set_id(self, id: str):
        """Set the hypervisor ID.

        Args:
            id (str): hypervisor ID.
        """
        self.id = id

    def get_id(self) -> str:
        """Get the hypervisor ID.

        Returns:
            str: hypervisor ID.
        """
        return self.id

    def set_hypervisor_hostname(self, hypervisor_hostname: str):
        """Set the hypervisor hostname.

        Args:
            hypervisor_hostname (str): hypervisor hostname.
        """
        self.hypervisor_hostname = hypervisor_hostname

    def get_hypervisor_hostname(self) -> str:
        """Get the hypervisor hostname.

        Returns:
            str: hypervisor hostname.
        """
        return self.hypervisor_hostname

    def set_hypervisor_type(self, hypervisor_type: str):
        """Set the hypervisor type.

        Args:
            hypervisor_type (str): hypervisor type.
        """
        self.hypervisor_type = hypervisor_type

    def get_hypervisor_type(self) -> str:
        """Get the hypervisor type.

        Returns:
            str: hypervisor type.
        """
        return self.hypervisor_type

    def set_host_ip(self, host_ip: str):
        """Set the hypervisor IP address.

        Args:
            host_ip (str): hypervisor IP address.
        """
        self.host_ip = host_ip

    def get_host_ip(self) -> str:
        """Get the hypervisor IP address.

        Returns:
            str: hypervisor IP address.
        """
        return self.host_ip

    def set_state(self, state: str):
        """Set the hypervisor state.

        Args:
            state (str): hypervisor state.
        """
        self.state = state

    def get_state(self) -> str:
        """Get the hypervisor state.

        Returns:
            str: hypervisor state.
        """
        return self.state

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Human-readable hypervisor list summary.
        """
        return f"HypervisorList(id={self.id}, hypervisor_hostname={self.hypervisor_hostname}, " f"hypervisor_type={self.hypervisor_type}, host_ip={self.host_ip}, " f"state={self.state})"
