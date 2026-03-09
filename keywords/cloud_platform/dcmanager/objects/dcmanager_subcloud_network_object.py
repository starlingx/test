class DcManagerSubcloudNetworkObject:
    """
    Object to represent network attributes for subcloud network configuration.
    """

    def __init__(self, management_subnet: str, management_gateway_address: str, 
                 management_start_address: str, management_end_address: str,
                 bootstrap_address: str, sysadmin_password: str):
        """
        Initialize DcManagerSubcloudNetworkObject.

        Args:
            management_subnet (str): Management subnet in CIDR format
            management_gateway_address (str): Management gateway IP address
            management_start_address (str): Start IP address of management range
            management_end_address (str): End IP address of management range
            bootstrap_address (str): Bootstrap IP address
            sysadmin_password (str): System admin password
        """
        self.management_subnet = management_subnet
        self.management_gateway_address = management_gateway_address
        self.management_start_address = management_start_address
        self.management_end_address = management_end_address
        self.bootstrap_address = bootstrap_address
        self.sysadmin_password = sysadmin_password

    def get_management_subnet(self) -> str:
        """Get management subnet."""
        return self.management_subnet

    def get_management_gateway_address(self) -> str:
        """Get management gateway address."""
        return self.management_gateway_address

    def get_management_start_address(self) -> str:
        """Get management start address."""
        return self.management_start_address

    def get_management_end_address(self) -> str:
        """Get management end address."""
        return self.management_end_address

    def get_bootstrap_address(self) -> str:
        """Get bootstrap address."""
        return self.bootstrap_address

    def get_sysadmin_password(self) -> str:
        """Get sysadmin password."""
        return self.sysadmin_password

    def __str__(self) -> str:
        """String representation of DcManagerSubcloudNetworkObject."""
        return (f"DcManagerSubcloudNetworkObject(management_subnet={self.management_subnet}, "
                f"management_gateway_address={self.management_gateway_address}, "
                f"management_start_address={self.management_start_address}, "
                f"management_end_address={self.management_end_address}, "
                f"bootstrap_address={self.bootstrap_address})")