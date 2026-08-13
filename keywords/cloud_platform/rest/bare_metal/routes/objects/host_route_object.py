"""Object class for host route."""


class HostRouteObject:
    """Represents a host route."""

    def __init__(self):
        """Initialize HostRouteObject."""
        self.uuid: str = None
        self.network: str = None
        self.gateway: str = None

    def set_uuid(self, uuid: str):
        """Set the UUID.

        Args:
            uuid (str): The route UUID.
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """Get the UUID.

        Returns:
            str: The route UUID.
        """
        return self.uuid

    def set_network(self, network: str):
        """Set the network.

        Args:
            network (str): The network address.
        """
        self.network = network

    def get_network(self) -> str:
        """Get the network.

        Returns:
            str: The network address.
        """
        return self.network

    def set_gateway(self, gateway: str):
        """Set the gateway.

        Args:
            gateway (str): The gateway address.
        """
        self.gateway = gateway

    def get_gateway(self) -> str:
        """Get the gateway.

        Returns:
            str: The gateway address.
        """
        return self.gateway
