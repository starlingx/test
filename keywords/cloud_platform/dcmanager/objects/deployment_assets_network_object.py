class DeploymentAssetsNetworkObject:
    """
    Represents a network configuration block parsed from a deployment assets YAML file.
    """

    def __init__(self):
        self.start_address: str = None
        self.end_address: str = None
        self.gateway_address: str = None
        self.subnet: str = None
        self.subnet_prefix: str = None

    def get_start_address(self) -> str:
        return self.start_address

    def set_start_address(self, start_address: str):
        self.start_address = start_address

    def get_end_address(self) -> str:
        return self.end_address

    def set_end_address(self, end_address: str):
        self.end_address = end_address

    def get_gateway_address(self) -> str:
        return self.gateway_address

    def set_gateway_address(self, gateway_address: str):
        self.gateway_address = gateway_address

    def get_subnet(self) -> str:
        return self.subnet

    def set_subnet(self, subnet: str):
        self.subnet = subnet

    def get_subnet_prefix(self) -> str:
        return self.subnet_prefix

    def set_subnet_prefix(self, subnet_prefix: str):
        self.subnet_prefix = subnet_prefix

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"start_address={self.start_address}, "
            f"end_address={self.end_address}, "
            f"gateway_address={self.gateway_address}, "
            f"subnet={self.subnet}, "
            f"subnet_prefix={self.subnet_prefix})"
        )
