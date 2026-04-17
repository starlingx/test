"""OpenStack floating ip list data object."""


class OpenStackFloatingIpListObject:
    """Object to represent the output of the 'openstack floating ip list' command."""
    
    def __init__(self):
        """Initialize OpenStackFloatingIpListObject."""
        self.id = None
        self.floating_ip_address = None
        self.fixed_ip_address = None
        self.port = None
        self.floating_network = None
        self.project = None
        
    def set_id(self, id: str):
        """Set the floating ip id.

        Args:
            id (str): floating ip id.
        """
        self.id = id
        
    def get_id(self) -> str:
        """Get the floating ip id.

        Returns:
            str: floating ip id.
        """
        return self.id

    def set_floating_ip_address(self, floating_ip_address: str):
        """Set the floating ip address.

        Args:
            floating_ip_address (str): floating ip address.
        """
        self.floating_ip_address = floating_ip_address

    def get_floating_ip_address(self) -> str:
        """Get the floating ip address.

        Returns:
            str: floating ip address.
        """
        return self.floating_ip_address

    def set_fixed_ip_address(self, fixed_ip_address: str):
        """Set the fixed ip address.

        Args:
            fixed_ip_address (str): fixed ip address.
        """
        self.fixed_ip_address = fixed_ip_address
        
    def get_fixed_ip_address(self) -> str:
        """Get the fixed ip address.

        Returns:
            str: fixed ip address.
        """
        return self.fixed_ip_address
    
    def set_port(self, port: str):
        """Set the floating ip port.
        
        Args:
            port (str): floating ip port.
        """
        self.port = port

    def get_port(self) -> str:
        """Get the floating ip port.

        Returns:
            str: floating ip port.
        """
        return self.port

    def set_floating_network(self, floating_network: str):
        """Set the floating ip network.

        Args:
            floating_network (str): floating ip network.
        """
        self.floating_network = floating_network

    def get_floating_network(self) -> str:
        """Get the floating ip network.

        Returns:
            str: floating ip network.
        """
        return self.floating_network

    def set_project(self, project: str):
        """Set the floating ip project.

        Args:
            project (str): floating ip project.
        """
        self.project = project

    def get_project(self) -> str:
        """Get the floating ip project.

        Returns:
            str: floating ip project.
        """
        return self.project

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Human-readable floating ip list summary.
        """
        return f"FloatingIpList(id={self.id}, floating_ip_address={self.floating_ip_address}, " f"fixed_ip_address={self.fixed_ip_address}, port={self.port}, " f"floating_network={self.floating_network}, project={self.project})"
