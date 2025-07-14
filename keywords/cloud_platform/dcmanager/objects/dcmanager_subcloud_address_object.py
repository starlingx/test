class DcManagerSubcloudAddressObject:
    """
    This class defines the object for subcloud BMC and bootstrap address information.
    """

    def __init__(
        self,
        bmc_address: str,
        bootstrap_address: str,
    ):
        """
        Constructor

        Args:
            bmc_address (str): BMC IP address
            bootstrap_address (str): IP address for initial subcloud controller
        """
        self.bmc_address = bmc_address
        self.bootstrap_address = bootstrap_address

    def get_bmc_address(self) -> str:
        """Get BMC IP address"""
        return self.bmc_address

    def get_bootstrap_address(self) -> str:
        """Get bootstrap address"""
        return self.bootstrap_address
